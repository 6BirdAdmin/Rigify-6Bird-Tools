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
import copy
from itertools import count
from rigify.base_rig import stage, BaseRig
from rigify.utils.rig import connected_children_names
from rigify.utils.misc import map_list
from rigify.utils.naming import make_derived_name
from rigify.utils.widgets import create_widget
from rigify.base_generate import BaseGenerator

class Rig(BaseRig):
    """A rig that generates a widget based on text."""

    def find_org_bones(self, bone):
        return [bone.name] + connected_children_names(self.obj, bone.name)

        text_input: str
        text_align_x: str
        text_align_y: str
        text_size: float
        text_extrude: float

    def initialize(self):
        self.text_input = self.params.text_input
        self.text_align_x = self.params.text_align_x
        self.text_align_y = self.params.text_align_y
        self.text_size = self.params.text_size
        self.text_extrude = self.params.text_extrude

    @stage.generate_bones
    def make_control_bones(self):
        org = self.bones.org
        self.bones.ctrl = map_list(self.make_control_bone, count(0), org)

    def make_control_bone(self, i, org):
        return self.copy_bone(org, make_derived_name(org, 'ctrl'), parent=True)

    ##############################
    # UI

    @classmethod
    def add_parameters(cls, params):
        params.text_input = bpy.props.StringProperty(
            name="Widget String",
            default='',
            description="Text to transform into widget."
        )
        params.text_align_x = bpy.props.EnumProperty(
            name="Align X",
            description="Select one of the options",
            items=[
                ('LEFT', 'Left', ''),
                ('CENTER', 'Center', ''),
                ('RIGHT', 'Right', ''),
                ('JUSTIFY', 'Justify', ''),
                ('FLUSH', 'Flush', ''),
            ],
            default='CENTER'
        )
        params.text_align_y = bpy.props.EnumProperty(
            name="Align Y",
            description="Select one of the options",
            items=[
                ('TOP', 'Top', ''),
                ('TOP_BASELINE', 'Top Baseline', ''),
                ('CENTER', 'Center', ''),
                ('BOTTOM_BASELINE', 'Bottom Baseline', ''),
                ('BOTTOM', 'Bottom', ''),
            ],
            default='CENTER'
        )
        params.text_size = bpy.props.FloatProperty(
            name="Text Size",
            default=1.0,
            description="Float Value."
        )
        params.text_extrude = bpy.props.FloatProperty(
            name="Extrude",
            default=0.0,
            description="Float Value."
        )

    @classmethod
    def parameters_ui(cls, layout, params):
        layout.row().prop(params, "text_input", text="Text")
        layout.row().prop(params, "text_size", text="Text Size")
        layout.row().prop(params, "text_extrude", text="Extrude")
        layout.row().prop(params, "text_align_x", text="Align X")
        layout.row().prop(params, "text_align_y", text="Align Y")

    @stage.generate_widgets
    def make_control_widgets(self):
        text_obj_name = self.bones.ctrl[0] + "_text_widget"
        text_existing_obj = bpy.data.objects.get(text_obj_name)
        if text_existing_obj:
            for collection in text_existing_obj.users_collection:
                collection.objects.unlink(text_existing_obj) 
            bpy.data.objects.remove(text_existing_obj)

        bpy.ops.object.text_add(location=(0, 0, 0))
        custom_shape = bpy.context.selected_objects[0]
        custom_shape.name = text_obj_name
        custom_shape.data.name = text_obj_name
        bpy.context.view_layer.objects.active = self.obj
        custom_shape.data.body = self.text_input or "Text"
        custom_shape.data.size = self.text_size
        custom_shape.data.extrude = self.text_extrude
        custom_shape.data.align_x = self.text_align_x
        custom_shape.data.align_y = self.text_align_y
        bpy.ops.object.convert(target='MESH')
        self.make_custom_widget(self.bones.ctrl[0], custom_shape)

    def make_custom_widget(self, ctrl, custom_shape):
            widget = create_widget(self.obj, ctrl, widget_force_new=True)
            widget.data = custom_shape.data
            widget.data.update()
            for collection in custom_shape.users_collection:
                collection.objects.unlink(custom_shape)
            generator = BaseGenerator.instance
            collection = generator.widget_collection
            generator.new_widget_table[self.text_input] = custom_shape
            collection.objects.link(custom_shape)
            return widget