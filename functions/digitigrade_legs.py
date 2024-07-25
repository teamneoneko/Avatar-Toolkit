import bpy
from ..core import common
from ..core import register_wrap
from .translations import t
import re


@register_wrap
class CreateDigitigradeLegs(bpy.types.Operator):
    bl_idname = "avatar_toolkit.createdigitigradelegs"
    bl_label = t('Tools.create_digitigrade_legs.label')
    bl_description = t('Tools.create_digitigrade_legs.desc')

    @classmethod
    def poll(cls, context):
        if(context.active_object is None):
            return False
        if(context.selected_editable_bones is not None):
            if(len(context.selected_editable_bones) == 2):
                return True
        return False

    def execute(self, context):

        for digi0 in context.selected_editable_bones:
            digi1: bpy.types.EditBone = None
            digi2: bpy.types.EditBone = None
            digi3: bpy.types.EditBone = None

            try:
                digi1 = digi0.children[0]
                digi2 = digi1.children[0]
                digi3 = digi2.children[0]
            except:
                self.report({'ERROR'}, t('Tools.digitigrade_legs.error.bone_format'))
                return {'CANCELLED'}
            digi4 = None
            try:
                digi4 = digi3.children[0]
                
            except:
                print("no toe bone. Continuing.")
            digi0.select = True
            digi1.select = True
            digi2.select = True
            digi3.select = True
            if(digi4):
                digi4.select = True
            bpy.ops.armature.roll_clear()
            bpy.ops.armature.select_all(action='DESELECT')

            #creating transform for upper leg
            digi0.select = True
            bpy.ops.transform.create_orientation(name="Toolkit_digi0", overwrite=True)
            bpy.ops.armature.select_all(action='DESELECT')


            #duplicate digi0 and assign it to thigh
            thigh = common.duplicatebone(digi0)
            bpy.ops.armature.select_all(action='DESELECT')

            #make digi2 parrallel to digi1
            digi2.align_orientation(digi0)

            #extrude thigh
            thigh.select_tail = True
            bpy.ops.armature.extrude_move(ARMATURE_OT_extrude={"forked":False},TRANSFORM_OT_translate=None)
            #set new bone to calf varible
            bpy.ops.armature.select_more()
            calf = context.selected_bones[0]
            bpy.ops.armature.select_all(action='DESELECT')

            #set calf end to  digi2 end
            calf.tail = digi2.tail

            #make copy of calf, flip it, and then align bone so that it's head is moved to match in align phase
            flipedcalf = common.duplicatebone(calf)
            bpy.ops.armature.select_all(action='DESELECT')
            flipedcalf.select = True
            bpy.ops.armature.switch_direction()
            bpy.ops.armature.select_all(action='DESELECT')
            flippeddigi1 = common.duplicatebone(digi1)
            bpy.ops.armature.select_all(action='DESELECT')
            flippeddigi1.select = True
            bpy.ops.armature.switch_direction()
            bpy.ops.armature.select_all(action='DESELECT')



            #align flipped calf to flipped middle leg to move the head
            flipedcalf.align_orientation(flippeddigi1)

            flipedcalf.length = flippeddigi1.length

            #assign calf tail to flipped calf head so it moves calf's tail to be out at the perfect parallelagram
            calf.head = flipedcalf.tail

            #delete helper bones
            bpy.ops.armature.select_all(action='DESELECT')
            flippeddigi1.select = True
            bpy.ops.armature.delete()
            bpy.ops.armature.select_all(action='DESELECT')
            flipedcalf.select = True
            bpy.ops.armature.delete()
            bpy.ops.armature.select_all(action='DESELECT')



            #reparent the foot to the new calf so it will be part of the new foot IK chain
            digi3.parent = calf
            #Tada! It's done! now to rename the old 3 segments that make up the old part to noik so resonite doesn't try to select them
            
            digi0.name = re.compile(re.escape("<noik>"), re.IGNORECASE).sub("",digi0.name)+"<noik>"
            digi1.name = re.compile(re.escape("<noik>"), re.IGNORECASE).sub("",digi1.name)+"<noik>"
            digi2.name = re.compile(re.escape("<noik>"), re.IGNORECASE).sub("",digi2.name)+"<noik>"
            #finally fully done!

        self.report({'INFO'}, t('Tools.digitigrade_legs.success'))
        return {'FINISHED'}