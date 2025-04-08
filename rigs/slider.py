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

# pylint: disable=fixme, import-error
import bpy


from itertools import count
from rigify.base_rig import stage, BaseRig
from rigify.utils.rig import connected_children_names
from rigify.utils.misc import map_list
from rigify.utils.bones import put_bone, copy_bone_properties, align_bone_orientation, set_bone_widget_transform
from rigify.utils.naming import make_derived_name
from rigify.utils.widgets_basic import create_bone_widget

class Rig(BaseRig):
    """A rig that generates a slider from a target bone."""

    def find_org_bones(self, bone):
        return [bone.name] + connected_children_names(self.obj, bone.name)

    ##############################
    # Control chain

    @stage.generate_bones

    def make_control_bones(self):
        org = self.bones.org
        slide_name = make_derived_name(org[0], 'ctrl', '_slide')
        slide_bone = self.copy_bone(org[0], slide_name)
        org.append(slide_bone)
        self.bones.ctrl = map_list(self.make_control_bone, count(0), org)

    def make_control_bone(self, i, org):
        return self.copy_bone(org, make_derived_name(org, 'ctrl'), parent=True)

    @stage.parent_bones
    def parent_controls(self):
        self.set_bone_parent(self.bones.org[1], self.bones.org[0])

    @stage.configure_bones
    def configure_controls(self):
        for args in zip(count(0), self.bones.ctrl, self.bones.org):
            self.configure_control_bone(*args)

    def configure_control_bone(self, i, ctrl, org):
        self.copy_bone_properties(org, ctrl)

    @stage.generate_widgets
    def make_control_widgets(self):
        for ctrl in self.bones.ctrl:
            self.make_control_widget(ctrl)

    def make_control_widget(self, ctrl):
        create_bone_widget(self.obj, ctrl)
