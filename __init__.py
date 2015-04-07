# Blender plug-in for exporting models to the zombye model format
# Copyright (C) 2015  Georg Schäfer
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

bl_info = {
	"name": "Export Zombye Model (.zmdl)",
	"author": "Georg Schäfer",
	"version": (0, 0, 1),
	"blender": (2, 69, 0),
	"location": "File > Export > Zombye Model (.zmdl)",
	"description": "The script exports models to zombye model format",
	"category": "Import-Export",
}

import bpy
from .zombye_exporter import export_zombye_model

def menu_func_export(self, context):
	self.layout.operator(export_zombye_model.bl_idname, text="Zombye Model (.zmdl)")

def register():
	bpy.utils.register_module(__name__)
	bpy.types.INFO_MT_file_export.append(menu_func_export)

def unregister():
	bpy.utils.unregister_module(__name__)
	bpy.types.INFO_MT_file_export.remove(menu_func_export)

if __name__ == "__main__":
	bpy.ops.zombye_tools.model('INVOKE_DEFAULT')
