import bpy
import os
import ssl
import json
import urllib
import shutil
import pathlib
import zipfile
from threading import Thread
from bpy.app.handlers import persistent
from ..functions.translations import t
from .addon_preferences import get_preference
from .register import register_wrap
from ..ui.panel import AvatarToolKit_PT_AvatarToolkitPanel, CATEGORY_NAME

GITHUB_REPO = "teamneoneko/Avatar-Toolkit-rinadev"

is_checking_for_update = False
update_needed = False
latest_version = None
latest_version_str = ''
version_list = None

main_dir = os.path.dirname(os.path.dirname(__file__))
downloads_dir = os.path.join(main_dir, "downloads")

@register_wrap
class AvatarToolkit_OT_CheckForUpdate(bpy.types.Operator):
    bl_idname = 'avatar_toolkit.check_for_update'
    bl_label = t('CheckForUpdateButton.label')
    bl_description = t('CheckForUpdateButton.desc')
    bl_options = {'INTERNAL'}

    def execute(self, context):
        check_for_update_background()
        return {'FINISHED'}

@register_wrap
class AvatarToolkit_OT_UpdateToLatest(bpy.types.Operator):
    bl_idname = 'avatar_toolkit.update_latest'
    bl_label = t('UpdateToLatestButton.label')
    bl_description = t('UpdateToLatestButton.desc')
    bl_options = {'INTERNAL'}

    def execute(self, context):
        update_now(latest=True)
        return {'FINISHED'}

@register_wrap
class AvatarToolkit_PT_UpdaterPanel(bpy.types.Panel):
    bl_label = t("Updater.label")
    bl_idname = "OBJECT_PT_avatar_toolkit_updater"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORY_NAME
    bl_parent_id = AvatarToolKit_PT_AvatarToolkitPanel.bl_idname
    bl_order = 5

    def draw(self, context):
        layout = self.layout
        draw_updater_panel(context, layout)

def check_for_update_background():
    global is_checking_for_update
    if is_checking_for_update:
        return

    is_checking_for_update = True
    Thread(target=check_for_update).start()

def check_for_update():
    global update_needed, latest_version, latest_version_str, version_list

    if not get_github_releases():
        finish_update_checking(error=t('check_for_update.cantCheck'))
        return

    update_needed = check_for_update_available()

    if update_needed:
        print('Update found!')
    else:
        print('No update found.')

    finish_update_checking()

def get_github_releases():
    global version_list
    version_list = {}

    try:
        ssl._create_default_https_context = ssl._create_unverified_context
        with urllib.request.urlopen(f'https://api.github.com/repos/{GITHUB_REPO}/releases') as url:
            data = json.loads(url.read().decode())
    except urllib.error.URLError:
        print('URL ERROR')
        return False

    for version in data:
        version_tag = version['tag_name']
        version_list[version_tag] = [
            version['zipball_url'],
            version['body'],
            version['published_at'].split('T')[0]
        ]

    return True

def check_for_update_available():
    global latest_version, latest_version_str
    if not version_list:
        return False

    latest_version = max(version_list.keys(), key=lambda v: [int(x) for x in v.split('.')])
    latest_version_str = latest_version

    current_version = get_preference("version")
    current_version_parts = [int(x) for x in current_version.split('.')]
    latest_version_parts = [int(x) for x in latest_version.split('.')]

    return latest_version_parts > current_version_parts

def finish_update_checking(error=''):
    global is_checking_for_update
    is_checking_for_update = False
    bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)

def update_now(latest=False):
    if latest:
        update_link = version_list[latest_version_str][0]
    else:
        update_link = version_list[bpy.context.scene.avatar_toolkit_updater_version_list][0]

    download_file(update_link)

def download_file(update_url):
    update_zip_file = os.path.join(downloads_dir, "avatar-toolkit-update.zip")

    if os.path.isdir(downloads_dir):
        shutil.rmtree(downloads_dir)

    pathlib.Path(downloads_dir).mkdir(exist_ok=True)

    try:
        ssl._create_default_https_context = ssl._create_unverified_context
        urllib.request.urlretrieve(update_url, update_zip_file)
    except urllib.error.URLError:
        finish_update(error=t('download_file.cantConnect'))
        return

    if not os.path.isfile(update_zip_file):
        finish_update(error=t('download_file.cantFindZip'))
        return

    with zipfile.ZipFile(update_zip_file, "r") as zip_ref:
        zip_ref.extractall(downloads_dir)

    os.remove(update_zip_file)

    extracted_zip_dir = find_init_directory(downloads_dir)
    if not extracted_zip_dir:
        finish_update(error=t('download_file.cantFindAvatarToolkit'))
        return

    clean_addon_dir()
    move_files(extracted_zip_dir, main_dir)
    shutil.rmtree(downloads_dir)

    finish_update()

def find_init_directory(path):
    for root, dirs, files in os.walk(path):
        if "__init__.py" in files:
            return root
    return None

def clean_addon_dir():
    for item in os.listdir(main_dir):
        item_path = os.path.join(main_dir, item)
        if item.startswith('.') or item in ['resources', 'downloads']:
            continue
        if os.path.isfile(item_path):
            os.remove(item_path)
        elif os.path.isdir(item_path):
            shutil.rmtree(item_path)

def move_files(from_dir, to_dir):
    for item in os.listdir(from_dir):
        s = os.path.join(from_dir, item)
        d = os.path.join(to_dir, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, dirs_exist_ok=True)
        else:
            shutil.copy2(s, d)

def finish_update(error=''):
    if error:
        print(f"Update failed: {error}")
    else:
        print("Update successful!")
    bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)

def get_version_list(self, context):
    return [(v, v, '') for v in version_list.keys()] if version_list else []

def draw_updater_panel(context, layout):
    col = layout.column(align=True)

    if is_checking_for_update:
        col.operator(AvatarToolkit_OT_CheckForUpdate.bl_idname, text=t('Updater.CheckForUpdateButton.label'))
    elif update_needed:
        col.operator(AvatarToolkit_OT_UpdateToLatest.bl_idname, text=t('Updater.UpdateToLatestButton.label', name=latest_version_str))
    else:
        col.operator(AvatarToolkit_OT_CheckForUpdate.bl_idname, text=t('Updater.CheckForUpdateButton.label_alt'))

    col.separator()
    row = col.row(align=True)
    row.prop(context.scene, 'avatar_toolkit_updater_version_list', text='')
    row.operator(AvatarToolkit_OT_UpdateToLatest.bl_idname, text=t('Updater.UpdateToSelectedButton.label'))

    col.separator()
    col.label(text=t('Updater.currentVersion').format(name=get_preference("version")))

