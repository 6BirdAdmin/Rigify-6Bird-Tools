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
from itertools import count
from mathutils import Matrix, Vector
from rigify.base_rig import stage, BaseRig
from rigify.utils.rig import connected_children_names
from rigify.utils.misc import map_list
from rigify.utils.bones import put_bone, copy_bone_properties, align_bone_orientation, set_bone_widget_transform
from rigify.utils.naming import make_derived_name
from rigify.utils.widgets_basic import create_bone_widget, create_line_widget
from rigify.utils.widgets import adjust_widget_transform_mesh

class Rig(BaseRig):
    """A rig that generates a slider from a target bone."""

    def find_org_bones(self, bone):
        return [bone.name] + connected_children_names(self.obj, bone.name)

    @stage.generate_bones

    def make_control_bones(self):
        org = self.bones.org
        slide_name = make_derived_name(org[0], 'org', '_slide')
        slide_bone = self.copy_bone(org[0], slide_name)
        org.append(slide_bone)
        self.bones.ctrl = map_list(self.make_control_bone, count(0), org)

    def make_control_bone(self, i, org):
        return self.copy_bone(org, make_derived_name(org, 'ctrl'), parent=True)

    @stage.parent_bones
    def parent_controls(self):
        self.set_bone_parent(self.bones.org[1], self.bones.org[0])
        self.set_bone_parent(self.bones.ctrl[1], self.bones.ctrl[0])

    @stage.configure_bones
    def configure_controls(self):
        arm = self.obj
        pb1 = arm.pose.bones[self.bones.ctrl[0]]
        bone1_length = pb1.bone.length
        for args in zip(count(0), self.bones.ctrl, self.bones.org):
            self.configure_control_bone(*args)
        self.make_constraint(self.bones.ctrl[1], 'LIMIT_LOCATION', space_object= self.obj, \
            space_subtarget= self.bones.ctrl[0], owner_space ='LOCAL', use_transform_limit=True, \
                max_y=bone1_length, use_max_x=True, use_max_y=True, \
                    use_max_z=True, use_min_x=True, use_min_y=True, use_min_z=True)

    def configure_control_bone(self, i, ctrl, org):
        self.copy_bone_properties(org, ctrl)

    @stage.rig_bones
    def rig_bones(self):
        self.add_slider_value()
        self.lock_bones()

    def add_slider_value(self):
        #Not gonna lie I got AI to figure this out, idk how it works
        bone1_name = self.bones.ctrl[0]
        bone2_name = self.bones.ctrl[1]
        custom_prop_name = "bone_distance"

        # Get objects and pose bones
        arm = self.obj
        pb1 = arm.pose.bones[bone1_name]
        pb2 = arm.pose.bones[bone2_name]
        bone1_length = pb1.bone.length

        # Add the custom property to bone_1
        pb1[custom_prop_name] = 0.0

        # Create driver for the custom property
        prop_path = f'pose.bones["{bone1_name}"]["{custom_prop_name}"]'
        fcurve = arm.driver_add(prop_path)
        driver = fcurve.driver
        driver.type = 'SCRIPTED'

        # Add variables for bone_1 and bone_2 world locations
        for bone, prefix in [(bone1_name, "a"), (bone2_name, "b")]:
            for axis in "XYZ":
                var = driver.variables.new()
                var.name = f"{prefix}_{axis}"
                var.type = 'TRANSFORMS'
                target = var.targets[0]
                target.id = arm
                target.bone_target = bone
                target.transform_type = f"LOC_{axis}"
                target.transform_space = 'WORLD_SPACE'

        driver.expression = (
            f"min(sqrt((a_X - b_X)**2 + (a_Y - b_Y)**2 + (a_Z - b_Z)**2) / {bone1_length:.6f}, 1.0)"
        )
    
    def lock_bones(self):
        arm = self.obj
        pb1 = arm.pose.bones[self.bones.ctrl[0]]
        pb2 = arm.pose.bones[self.bones.ctrl[1]]
        pb1.lock_rotations_4d = True
        pb2.lock_rotations_4d = True
        pb1.lock_rotation_w = True
        pb2.lock_rotation_w = True
        pb1.lock_rotation = [True, True, True]
        pb2.lock_rotation = [True, True, True]
        pb1.lock_scale = [True, True, True]
        pb2.lock_scale = [True, True, True]
        pb1.lock_location = [True, True, True]

    @stage.generate_widgets
    def make_control_widgets(self):
        ctrl = self.bones.ctrl
        line = create_line_widget(self.obj, ctrl[0])
        slider = create_bone_widget(self.obj, ctrl[1])
        transform = Matrix.Scale(0.025, 4, Vector((0.0, 1.0, 0.0)))
        adjust_widget_transform_mesh(slider, transform, local=True)
        