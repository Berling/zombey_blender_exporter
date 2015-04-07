import bpy
import json
import bmesh

def mesh_data(mesh):
	meshdata = {}
	vertices = []
	indices = []
	submeshes = {}

	uv_layer = mesh.loops.layers.uv.active
	if uv_layer is None:
		raise TypeError("mesh %s has no active uv layer" %mesh.name)

	for face in mesh.faces:
		triangle = []

		material_index = face.material_index
		material = bpy.data.materials[material_index]
		if material.name not in submeshes:
			submeshes[material.name] = {}
			submeshes[material.name]["indices"] = []
			submeshes[material.name]["textures"] = {}

			texture_slots = material.texture_slots
			if "diffuse" not in texture_slots:
				raise ValueError("material %s has no diffuse texture" %material.name)
			if "normal" not in texture_slots:
				raise ValueError("material %s has no normal texture" %material.name)
			if "material" not in texture_slots:
				raise ValueError("material %s has no material texture" %material.name)

			submeshes[material.name]["textures"]["diffuse"] = bpy.path.abspath(texture_slots["diffuse"].texture.image.filepath)
			submeshes[material.name]["textures"]["normal"] = bpy.path.abspath(texture_slots["normal"].texture.image.filepath)
			submeshes[material.name]["textures"]["material"] = bpy.path.abspath(texture_slots["material"].texture.image.filepath)

		for loop in face.loops:
			vert = loop.vert
			pos = vert.co
			nor = face.normal
			if face.smooth:
				nor = vert.normal

			uv = loop[uv_layer].uv

			vertexattributes = {}
			vertexattributes["position"] = [pos.x, pos.z, -pos.y]
			vertexattributes["texcoord"] = [uv.x, uv.y]
			vertexattributes["normal"] = [nor.x, nor.z, -nor.y]
			if vertices.count(vertexattributes) == 0:
				vertices.append(vertexattributes)

			triangle.append(vertices.index(vertexattributes))

		submeshes[material.name]["indices"].append(triangle)

	meshdata["vertices"] = vertices
	meshdata["submeshes"] = submeshes

	return meshdata

def dump_json(file, data):
	file.write(json.dumps(data, indent="\t", separators=(',',' : ')))

def write_model_data(context, filepath, use_some_setting):
	f = open(filepath, 'w', encoding='utf-8')
	meshes = {}
	for mesh in bpy.data.meshes:
		if mesh.users > 0:
			bm = bmesh.new()
			bm.from_mesh(mesh)
			bmesh.ops.triangulate(bm, faces=bm.faces)
			meshes[mesh.name] = mesh_data(bm)
			bm.free()
			del bm

	dump_json(f, meshes)

	f.close()

	return {'FINISHED'}


# ExportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator


class export_zombye_model(Operator, ExportHelper):
	"""This appears in the tooltip of the operator and in the generated docs"""
	bl_idname = "export_test.some_data"  # important since its how bpy.ops.import_test.some_data is constructed
	bl_label = "Export ZMDL"

	# ExportHelper mixin class uses this
	filename_ext = ".zmdl"

	filter_glob = StringProperty(
			default="*.zmdl",
			options={'HIDDEN'},
			)

	# List of operator properties, the attributes will be assigned
	# to the class instance from the operator settings before calling.
	use_setting = BoolProperty(
			name="Example Boolean",
			description="Example Tooltip",
			default=True,
			)

	type = EnumProperty(
			name="Example Enum",
			description="Choose between two items",
			items=(('OPT_A', "First Option", "Description one"),
				   ('OPT_B', "Second Option", "Description two")),
			default='OPT_A',
			)

	def execute(self, context):
		return write_model_data(context, self.filepath, self.use_setting)


# Only needed if you want to add into a dynamic menu
def menu_func_export(self, context):
	self.layout.operator(export_zombye_model.bl_idname, text="Text Export Operator")


def register():
	bpy.utils.register_class(export_zombye_model)
	bpy.types.INFO_MT_file_export.append(menu_func_export)


def unregister():
	bpy.utils.unregister_class(export_zombye_model)
	bpy.types.INFO_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
	register()

	# test call
	bpy.ops.export_test.some_data('INVOKE_DEFAULT')
