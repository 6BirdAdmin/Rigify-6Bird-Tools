# ====================== BEGIN GPL LICENSE BLOCK ======================
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ======================= END GPL LICENSE BLOCK ========================

import bpy
import math
from itertools import count
from mathutils import Matrix, Vector
from rigify.base_rig import stage, BaseRig
from rigify.utils.rig import connected_children_names
from rigify.utils.misc import map_list
from rigify.utils.bones import copy_bone_properties
from rigify.utils.naming import make_derived_name
from rigify.utils.widgets_basic import create_circle_widget, create_cube_widget
from rigify.utils.widgets import adjust_widget_transform_mesh
from rigify.rig_ui_template import PanelLayout

class Rig(BaseRig):
    """A rig that generates a switch from a target bone."""

    def find_org_bones(self, bone):
        return [bone.name] + connected_children_names(self.obj, bone.name)

    @stage.generate_bones
    def make_control_bones(self):
        org = self.bones.org
        switch_on_name = make_derived_name(org[0], 'org', '_on')
        switch_off_name = make_derived_name(org[0], 'org', '_off')
        on_bone = self.copy_bone(org[0], switch_on_name)
        off_bone = self.copy_bone(org[0], switch_off_name)
        org.append(on_bone)
        org.append(off_bone)
        self.bones.ctrl = map_list(self.make_control_bone, count(0), org)
        # This creates the following in self.bones.ctrl: [container bone, on bone, off bone]


    def make_control_bone(self, i, org):
        return self.copy_bone(org, make_derived_name(org, 'ctrl'), parent=True)

    @stage.parent_bones
    def parent_controls(self):
        self.set_bone_parent(self.bones.org[1], self.bones.org[0])
        self.set_bone_parent(self.bones.org[1], self.bones.org[0])
        self.set_bone_parent(self.bones.ctrl[2], self.bones.ctrl[0])
        self.set_bone_parent(self.bones.ctrl[2], self.bones.ctrl[0])


    @stage.configure_bones
    def configure_controls(self):
        arm = self.obj
        pb1 = arm.pose.bones[self.bones.ctrl[0]]
        bone1_length = pb1.bone.length
        for args in zip(count(0), self.bones.ctrl, self.bones.org):
            self.configure_control_bone(*args)

    def configure_control_bone(self, i, ctrl, org):
        self.copy_bone_properties(org, ctrl)


    @stage.rig_bones
    def setup_bones(self):
        self.add_switch_value()

    def add_switch_value(self):
        bone1_name = self.bones.ctrl[0]
        bone2_name = self.bones.ctrl[1]
        bone3_name = self.bones.ctrl[2]
        custom_prop_name = "switch_value"

        # Get objects and pose bones
        arm = self.obj
        container = arm.pose.bones[bone1_name]
        on_bone = arm.pose.bones[bone2_name]
        off_bone = arm.pose.bones[bone3_name]
        container_length = container.bone.length

        # Add the custom property to switch
        if custom_prop_name not in container.keys():
            bpy.types.PoseBone.__annotations__[custom_prop_name] = bpy.props.BoolProperty(
                name="Active",
                description="True if the slider is closer to the ON position",
                default=False
            )
            container[custom_prop_name] = False

        on_bone.bone.hide = True
        self.obj["last_selected"] = ""


    @stage.generate_widgets
    def make_control_widgets(self):
        ctrl = self.bones.ctrl
        bone1_length = self.obj.pose.bones[ctrl[0]].length
        box = create_cube_widget(self.obj, ctrl[0])
        switch = create_circle_widget(self.obj, ctrl[1])
        switch = create_circle_widget(self.obj, ctrl[2])


        transform_box = Matrix.Translation((0.0, bone1_length/2, 0.0)) @ Matrix.Scale(0.001, 4, Vector((0, 0, 1))) @ Matrix.Scale(1.2, 4, Vector((0, 1, 0))) @ Matrix.Scale(0.2, 4, Vector((1, 0, 0)))
        transform_switch =  Matrix.Rotation(math.radians(90), 4, 'X') @ Matrix.Scale(0.1, 4, Vector((1, 0, 0))) @ Matrix.Scale(0.1, 4, Vector((0, 0, 1)))
        adjust_widget_transform_mesh(box, transform_box, local=self.obj.pose.bones[ctrl[0]])
        adjust_widget_transform_mesh(switch, transform_switch, local=True)

    @stage.finalize
    def add_toggle_handler_logic(self):
        Bone_C = self.bones.ctrl[0]
        Bone_A = self.bones.ctrl[1]
        Bone_B = self.bones.ctrl[2]
        SCRIPT_UTILITIES_TOGGLE_BONES_ON_SELECT = ['''
def toggle_bones_on_select(scene):
    obj = bpy.context.object

    if not obj or obj.type != 'ARMATURE' or bpy.context.mode != 'POSE':
        return

    try:
        sel_bone = obj.data.bones.active.name
    except:
        return

    if sel_bone not in [{Bone_A}, {Bone_B}]:
        return

    if obj.get("last_selected", "") == sel_bone:
        return  # already handled

    bones = obj.data.bones
    pose_bones = obj.pose.bones

    bone_c = pose_bones[{Bone_C}]
    current_value = bool(bone_c.get("flipped", False))
    new_value = not current_value
    bone_c["flipped"] = new_value

    # Insert keyframe
    bone_c.keyframe_insert(data_path='["flipped"]', frame=bpy.context.scene.frame_current)

    # Toggle visibility
    if sel_bone == {Bone_A}:
        bones[{Bone_A}].hide = True
        bones[{Bone_B}].hide = False
    elif sel_bone == {Bone_B}:
        bones[{Bone_B}].hide = True
        bones[{Bone_A}].hide = False

    obj["last_selected"] = sel_bone

    def register_handler():
        if toggle_bones_on_select not in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.append(toggle_bones_on_select)


    def unregister_handler():
        if toggle_bones_on_select in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.remove(toggle_bones_on_select)

    if __name__ == "__main__":
        register_handler()
                ''']
        self.generator.script.add_utilities(SCRIPT_UTILITIES_TOGGLE_BONES_ON_SELECT)

    
    