import bpy
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper
from ..core.register import register_wrap
from ..core.importer import imports, import_types
from ..core.common import remove_default_objects
from ..functions.translations import t
import pathlib
import os

VRM_IMPORTER_URL = "https://github.com/saturday06/VRM_Addon_for_Blender"

@register_wrap
class AvatarToolKit_OT_ImportAnyModel(Operator, ImportHelper):
    bl_idname = 'avatar_toolkit.import_any_model'
    bl_label = t('Tools.import_any_model.label')
    bl_description = t('Tools.import_any_model.desc')
    bl_options = {'REGISTER', 'UNDO'}
    files: bpy.props.CollectionProperty(type=bpy.types.OperatorFileListElement, options={'HIDDEN', 'SKIP_SAVE'})
    
    filter_glob: bpy.props.StringProperty(default=imports, options={'HIDDEN', 'SKIP_SAVE'})
    directory: bpy.props.StringProperty(maxlen=1024, subtype='FILE_PATH', options={'HIDDEN', 'SKIP_SAVE'})

    # since I wrote this myself, a bit more efficient than cats. mostly - @989onan
    def execute(self, context: bpy.types.Context):
        file_grouping_dict: dict[str, list[dict[str, str]]] = dict()  # group our files so our importers can import them together. in the case of OBJ+MTL and others that need grouped files, this is extremely important.
        remove_default_objects()
        # check if we are importing multiple files
        is_multi = len(self.files) > 0

        if is_multi:
            for file in self.files:
                fullpath = os.path.join(self.directory, os.path.basename(file.name))
                name = pathlib.Path(fullpath).suffix.replace(".", "")
                # this makes sure our imports that should be grouped stay together.
                # basically the method checks for if the first value has a lambda with the same bytecode as another lambda, then it will use that value's key (ex:"obj"<->"mtl" or "fbx"), keeping same importers together
                if name not in file_grouping_dict:
                    file_grouping_dict[name] = []
                file_grouping_dict[name].append({"name": os.path.basename(file.name)})  # emulate passing a list of files.
        else:
            fullpath: str = os.path.join(os.path.dirname(self.filepath), os.path.basename(self.filepath))
            name = pathlib.Path(fullpath).suffix.replace(".", "")
            if name not in file_grouping_dict:
                file_grouping_dict[name] = []
            file_grouping_dict[name].append({"name": fullpath})  # emulate passing a list of files.

        # import the files together to make sure things like obj import together. This is important
        for file_group_name, files in file_grouping_dict.items():
            try:
                # Check for VRM importer availability
                if file_group_name == "vrm" and not hasattr(bpy.ops.import_scene, "vrm"):
                    bpy.ops.wm.vrm_importer_popup('INVOKE_DEFAULT')
                    return {'CANCELLED'}

                if self.directory:
                    import_types[file_group_name](self.directory, files, self.filepath)
                else:
                    import_types[file_group_name]("", files, self.filepath)  # give an empty directory, works just fine for 90%
            except AttributeError as e:
                if file_group_name == "vrm":
                    bpy.ops.wm.vrm_importer_popup('INVOKE_DEFAULT')
                else:
                    self.report({'ERROR'}, t('Importing.need_importer').format(extension=file_group_name))
                print("Importer error:", e)
                return {'CANCELLED'}

        self.report({'INFO'}, t('Quick_Access.import_success'))
        return {'FINISHED'}

@register_wrap
class VRMImporterPopup(Operator):
    bl_idname = "wm.vrm_importer_popup"
    bl_label = "VRM Importer Not Installed"

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context):
        layout = self.layout
        layout.label(text="VRM importer plugin is not installed.")
        layout.label(text="Please install it to import VRM files.")
        layout.operator("wm.url_open", text="Get VRM Importer").url = VRM_IMPORTER_URL

#TODO: This needs to be done with our own MMD importer.
""" 
#stolen from cats. Oh wait I made this code riiiiiiight - @989onan
@register_wrap
class ImportMMDAnimation(bpy.types.Operator, ImportHelper):
    bl_idname = 'avatar_toolkit.import_mmd_animation'
    bl_label = t('Importer.mmd_anim_importer.label')
    bl_description = t('Importer.mmd_anim_importer.desc')
    bl_options = {'INTERNAL', 'UNDO'}

    filter_glob: bpy.props.StringProperty(
        default="*.vmd",
        options={'HIDDEN'}
    )
    files: bpy.props.CollectionProperty(type=bpy.types.OperatorFileListElement, options={'HIDDEN', 'SKIP_SAVE'})
    directory: bpy.props.StringProperty(maxlen=1024, subtype='FILE_PATH', options={'HIDDEN', 'SKIP_SAVE'})
    filepath: bpy.props.StringProperty()

    @classmethod
    def poll(cls, context):
        if common.get_armature(context) is None:
            return False
        return True

    def execute(self, context):

        # Make sure that the first layer is visible
        if hasattr(context.scene, 'layers'):
            context.scene.layers[0] = True

        filename, extension = os.path.splitext(self.filepath)

        if(extension == ".vmd"):

            #A dictionary to change the current model to MMD importer compatable temporarily
            bonedict = {
                "chest":"UpperBody",
                "neck":"Neck",
                "head":"Head",
                "hips":"Center",
                "spine":"LowerBody",

                "right_wrist":"Wrist_R",
                "right_elbow":"Elbow_R",
                "right_arm":"Arm_R",
                "right_shoulder":"Shoulder_R",
                "right_leg":"Leg_R",
                "right_knee":"Knee_R",
                "right_ankle":"Ankle_R",
                "right_toe":"Toe_R",


                "left_wrist":"Wrist_L",
                "left_elbow":"Elbow_L",
                "left_arm":"Arm_L",
                "left_shoulder":"Shoulder_L",
                "left_leg":"Leg_L",
                "left_knee":"Knee_L",
                "left_ankle":"Ankle_L",
                "left_toe":"Toe_L"

            }

            armature = common.get_armature(context)
            common.unselect_all()
            common.Set_Mode(context, 'OBJECT')
            common.unselect_all()
            common.set_active(armature)
            
            orig_names = dict()
            reverse_bone_lookup = dict()
            for (preferred_name, name_list) in bone_names.items():
                for name in name_list:
                    reverse_bone_lookup[name] = preferred_name
            

            for bone in armature.data.bones:
                if common.simplify_bonename(bone.name) in reverse_bone_lookup and reverse_bone_lookup[common.simplify_bonename(bone.name)] in bonedict:
                    orig_names[bonedict[reverse_bone_lookup[common.simplify_bonename(bone.name)]]] = bone.name
                    bone.name = bonedict[reverse_bone_lookup[common.simplify_bonename(bone.name)]]
            try:
                bpy.ops.mmd_tools.import_vmd(filepath=self.filepath,bone_mapper='RENAMED_BONES',use_underscore=True, dictionary='INTERNAL')
            except AttributeError as e:
                print("importer error was:")
                print(e)
                print(t('Importing.importer_search_term'))
                common.open_web_after_delay_multi_threaded(delay=12, url=t('Importing.importer_search_term').format(extension = "MMD"))
                self.report({'ERROR'},t('Importing.need_importer').format(extension = "MMD"))
                
                return {'CANCELLED'}

            #iterate through bones and put them back, therefore blender API will change the animation to be correct.
            #this is because renaming bones fixes the animation targets in the data model.
            for bone in armature.data.bones:
                if common.simplify_bonename(bone.name) in orig_names:
                    bone.name = orig_names[common.simplify_bonename(bone.name)]
            
            common.unselect_all()
            common.Set_Mode(context, 'OBJECT')
            common.unselect_all()
            common.set_active(armature)
        
        return {'FINISHED'} """