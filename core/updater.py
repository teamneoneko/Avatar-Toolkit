import bpy
import os
import ssl
import json
import urllib
import shutil
import pathlib
import zipfile
import time 
from urllib import request, error
from threading import Thread
from bpy.app.handlers import persistent
from .translations import t
from .addon_preferences import get_preference, get_current_version, save_preference
from ..ui.main_panel import AvatarToolKit_PT_AvatarToolkitPanel, CATEGORY_NAME
from typing import Dict, List, Tuple, Optional, Set, Any

GITHUB_REPO = "teamneoneko/Avatar-Toolkit"

is_checking_for_update: bool = False
update_needed: bool = False
latest_version: Optional[str] = None
latest_version_str: str = ''
version_list: Optional[Dict[str, List[str]]] = None

main_dir: str = os.path.dirname(os.path.dirname(__file__))
downloads_dir: str = os.path.join(main_dir, "downloads")


class AvatarToolkit_OT_CheckForUpdate(bpy.types.Operator):
    bl_idname = 'avatar_toolkit.check_for_update'
    bl_label = t('CheckForUpdateButton.label')
    bl_description = t('CheckForUpdateButton.desc')
    bl_options = {'INTERNAL'}

    def execute(self, context: bpy.types.Context) -> Set[str]:
        check_for_update_background()
        return {'FINISHED'}


class AvatarToolkit_OT_UpdateToLatest(bpy.types.Operator):
    bl_idname = 'avatar_toolkit.update_latest'
    bl_label = t('UpdateToLatestButton.label')
    bl_description = t('UpdateToLatestButton.desc')
    bl_options = {'INTERNAL'}

    def execute(self, context: bpy.types.Context) -> Set[str]:
        update_now(latest=True)
        return {'FINISHED'}


class AvatarToolkit_OT_UpdateNotificationPopup(bpy.types.Operator):
    bl_idname = "avatar_toolkit.update_notification_popup"
    bl_label = t('UpdateNotificationPopup.label')
    bl_description = t('UpdateNotificationPopup.desc')
    bl_options = {'INTERNAL'}

    def execute(self, context: bpy.types.Context) -> Set[str]:
        update_now(latest=True)
        self.report({'INFO'}, "Update started. Please wait for the process to complete.")
        return {'FINISHED'}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> Set[str]:
        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        col = layout.column(align=True)
        col.label(text=t('UpdateNotificationPopup.newUpdate', default="New update available: {version}").format(version=latest_version_str))


class AvatarToolkit_PT_UpdaterPanel(bpy.types.Panel):
    bl_label = t("Updater.label")
    bl_idname = "OBJECT_PT_avatar_toolkit_updater"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORY_NAME
    bl_parent_id = AvatarToolKit_PT_AvatarToolkitPanel.bl_idname
    bl_order = 1

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        draw_updater_panel(context, layout)


class AvatarToolkit_OT_RestartBlenderPopup(bpy.types.Operator):
    bl_idname = "avatar_toolkit.restart_blender_popup"
    bl_label = t('RestartBlenderPopup.label', default="Restart Blender")
    bl_description = t('RestartBlenderPopup.desc', default="Restart Blender to complete the update")
    bl_options = {'INTERNAL'}

    def execute(self, context: bpy.types.Context) -> Set[str]:
        return {'FINISHED'}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> Set[str]:
        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        col = layout.column(align=True)
        col.label(text=t('RestartBlenderPopup.message', default="Update successful! Please restart Blender."))

@persistent
def check_for_update_on_start(dummy: Any) -> None:
    if get_preference("check_for_updates_on_startup", True):
        current_time = time.time()
        last_check = get_preference("last_update_check", 0)
        if current_time - last_check > 86400:  # 24 hours
            check_for_update_background()
            save_preference("last_update_check", current_time)

def check_for_update_background() -> None:
    global is_checking_for_update
    if is_checking_for_update:
        return

    is_checking_for_update = True
    Thread(target=check_for_update).start()

def check_for_update() -> None:
    global update_needed, latest_version, latest_version_str, version_list

    if not get_github_releases():
        bpy.app.timers.register(lambda: finish_update_checking(error=t('check_for_update.cantCheck')))
        return

    update_needed = check_for_update_available()

    if update_needed:
        print('Update found!')
        bpy.app.timers.register(lambda: bpy.ops.avatar_toolkit.update_notification_popup('INVOKE_DEFAULT') or None)
    else:
        print('No update found.')

    bpy.app.timers.register(finish_update_checking)

def get_github_releases() -> bool:
    global version_list
    version_list = {}

    try:
        ssl._create_default_https_context = ssl._create_unverified_context
        with request.urlopen(f'https://api.github.com/repos/{GITHUB_REPO}/releases') as url:
            data = json.loads(url.read().decode())
    except error.URLError:
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

def check_for_update_available() -> bool:
    global latest_version, latest_version_str
    if not version_list:
        return False

    latest_version = max(version_list.keys(), key=lambda v: [int(x) for x in v.split('.')])
    latest_version_str = latest_version

    current_version = get_current_version()
    print(f"Current version: {current_version}")  # Debugging statement

    if current_version is None:
        print("Current version is None. Cannot check for updates.")
        return False

    try:
        # Validate that the version string contains only numeric parts
        current_version_parts = [int(x) for x in current_version.split('.')]
        latest_version_parts = [int(x) for x in latest_version.split('.')]
    except ValueError as e:
        print(f"Error parsing version numbers: {e}")
        return False

    return latest_version_parts > current_version_parts


def finish_update_checking(error: str = '') -> None:
    global is_checking_for_update
    is_checking_for_update = False
    if update_needed:
        bpy.ops.avatar_toolkit.update_notification_popup('INVOKE_DEFAULT')
    ui_refresh()
    return None  # Important for bpy.app.timers

def update_now(latest: bool = False) -> None:
    if not version_list:
        print("No version list available. Please check for updates first.")
        return
        
    if latest:
        update_link = version_list[latest_version_str][0]
    else:
        update_link = version_list[bpy.context.scene.avatar_toolkit_updater_version_list][0]

    download_file(update_link)
    ui_refresh()

def download_file(update_url: str) -> None:
    update_zip_file = os.path.join(downloads_dir, "avatar-toolkit-update.zip")

    if os.path.isdir(downloads_dir):
        shutil.rmtree(downloads_dir)

    pathlib.Path(downloads_dir).mkdir(exist_ok=True)

    try:
        ssl._create_default_https_context = ssl._create_unverified_context
        urllib.request.urlretrieve(update_url, update_zip_file)
    except error.URLError:
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

def find_init_directory(path: str) -> Optional[str]:
    for root, dirs, files in os.walk(path):
        if "__init__.py" in files:
            return root
    return None

def clean_addon_dir() -> None:
    for item in os.listdir(main_dir):
        item_path = os.path.join(main_dir, item)
        if item.startswith('.') or item in ['resources', 'downloads']:
            continue
        if os.path.isfile(item_path):
            os.remove(item_path)
        elif os.path.isdir(item_path):
            shutil.rmtree(item_path)

def move_files(from_dir: str, to_dir: str) -> None:
    for item in os.listdir(from_dir):
        s = os.path.join(from_dir, item)
        d = os.path.join(to_dir, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, dirs_exist_ok=True)
        else:
            shutil.copy2(s, d)

def finish_update(error: str = '') -> None:
    if error:
        print(f"Update failed: {error}")
    else:
        print("Update successful!")
        save_preference("version", latest_version_str)
        bpy.ops.avatar_toolkit.restart_blender_popup('INVOKE_DEFAULT')
    ui_refresh()

def get_version_list(self, context: bpy.types.Context) -> List[Tuple[str, str, str]]:
    return [(v, v, '') for v in version_list.keys()] if version_list else []

def draw_updater_panel(context: bpy.types.Context, layout: bpy.types.UILayout) -> None:
    box = layout.box()
    col = box.column(align=True)
    
    # Header
    row = col.row()
    row.scale_y = 1.2
    row.label(text=t('Updater.label'), icon='DOWNARROW_HLT')
    
    col.separator()
    
    # Update check/status section
    if is_checking_for_update:
        col.operator(AvatarToolkit_OT_CheckForUpdate.bl_idname, 
                    text=t('Updater.CheckForUpdateButton.label'),
                    icon='SORTTIME')
    elif update_needed:
        update_row = col.row(align=True)
        update_row.scale_y = 1.5
        update_row.alert = True
        update_row.operator(AvatarToolkit_OT_UpdateToLatest.bl_idname, 
                          text=t('Updater.UpdateToLatestButton.label', name=latest_version_str),
                          icon='IMPORT')
    else:
        col.operator(AvatarToolkit_OT_CheckForUpdate.bl_idname, 
                    text=t('Updater.CheckForUpdateButton.label_alt'),
                    icon='FILE_REFRESH')

    # Version selection section
    col.separator()
    box_inner = col.box()
    box_inner.label(text=t('Updater.selectVersion'), icon='SETTINGS')
    row = box_inner.row(align=True)
    row.prop(context.scene.avatar_toolkit, 'avatar_toolkit_updater_version_list', text='')
    row.operator(AvatarToolkit_OT_UpdateToLatest.bl_idname, 
                text=t('Updater.UpdateToSelectedButton.label'),
                icon='IMPORT')

    # Current version info
    col.separator()
    curr_ver_row = col.row()
    curr_ver_row.label(text=t('Updater.currentVersion').format(name=get_current_version()),
                      icon='CHECKMARK')

def ui_refresh() -> None:
    for windowManager in bpy.data.window_managers:
        for window in windowManager.windows:
            for area in window.screen.areas:
                area.tag_redraw()
