import bpy
import json
import bmesh
from mathutils import Matrix

def mesh_data(obj, anim_data):
	mesh = bmesh.new()
	mesh.from_mesh(obj.data)
	bmesh.ops.triangulate(mesh, faces=mesh.faces)
	name = obj.data.name
	write_weights = False
	vertex_groups = obj.vertex_groups
	dvert_layer = mesh.verts.layers.deform.active

	if dvert_layer is None:
		raise ValueError("object has no vertex groups")

	materials = obj.material_slots
	meshdata = {}
	vertices = []
	indices = []
	submeshes = {}

	uv_layer = mesh.loops.layers.uv.active
	if uv_layer is None:
		raise TypeError("mesh %s has no active uv layer" %name)

	for face in mesh.faces:
		triangle = []

		material_index = face.material_index
		material = materials[material_index].material
		if material.name not in submeshes:
			submeshes[material.name] = {}
			submeshes[material.name]["indices"] = []
			submeshes[material.name]["textures"] = {}

			texture_slots = material.texture_slots
			diffuse_texture = [value for key, value in texture_slots.items() if "diffuse" in key]
			if not diffuse_texture:
				raise ValueError("material %s has no diffuse texture" %material.name)
			normal_texture = [value for key, value in texture_slots.items() if "normal" in key]
			if not normal_texture:
				raise ValueError("material %s has no normal texture" %material.name)
			material_texture = [value for key, value in texture_slots.items() if "material" in key]
			if not material_texture:
				raise ValueError("material %s has no material texture" %material.name)

			submeshes[material.name]["textures"]["diffuse"] = bpy.path.abspath(diffuse_texture[0].texture.image.filepath)
			submeshes[material.name]["textures"]["normal"] = bpy.path.abspath(normal_texture[0].texture.image.filepath)
			submeshes[material.name]["textures"]["material"] = bpy.path.abspath(material_texture[0].texture.image.filepath)

		for loop in face.loops:
			vert = loop.vert
			pos = vert.co
			nor = face.normal
			if face.smooth:
				nor = vert.normal

			uv = loop[uv_layer].uv

			vertexattributes = {}
			vertexattributes["position"] = [pos.x, pos.z, -pos.y]
			vertexattributes["texcoord"] = [uv.x, -uv.y]
			vertexattributes["normal"] = [nor.x, nor.z, -nor.y]
			if vertices.count(vertexattributes) == 0:
				vertices.append(vertexattributes)

			triangle.append(vertices.index(vertexattributes))

			if anim_data is not None:
				dvert = vert[dvert_layer]
				if len(dvert.values()) > 4:
					raise ValueError("vertex is assigned to too many vertex groups")
				if len(dvert.values()) == 0:
					parent_name = vertex_groups
					vertexattributes["indices"] = [0]
					vertexattributes["weights"] = [1.0]
				else:
					vertexattributes["indices"] = []
					vertexattributes["weights"] = []
					for key, value in dvert.items():
						bone_name = vertex_groups[key].name
						index = anim_data["skeleton"][bone_name]["id"]
						vertexattributes["indices"].append(index)
						vertexattributes["weights"].append(value)

		submeshes[material.name]["indices"].append(triangle)

	meshdata["vertices"] = vertices
	meshdata["submeshes"] = submeshes

	mesh.free()
	del mesh

	modeldata = {}
	modeldata.update(meshdata)
	modeldata.update(anim_data)

	return modeldata

def anim_data(armature):
	armature_data = {}
	armature_data["skeleton"] = {}
	bone_ids = {}
	ids = 0

	for bone in armature.bones:
		bone_data = {}
		if bone.name not in bone_ids:
			bone_ids[bone.name] = ids
			ids += 1
		bone_data["id"] = bone_ids[bone.name]
		parent = bone.parent
		if parent is None:
			bone_data["parent"] = None
		else:
			if parent.name not in bone_ids:
				bone_ids[parent.name] = ids
				ids += 1
			bone_data["parent"] = bone_ids[parent.name]

		transformation = bone.matrix_local
		pos = transformation.to_translation()
		bone_data["translation"] = [pos.x, pos.z, -pos.y]
		rot = transformation.to_quaternion()
		bone_data["rotation"] = [rot.w, rot.x, rot.y, rot.z]
		scale = transformation.to_scale()
		bone_data["scale"] = [scale.x, scale.z, -scale.y]

		armature_data["skeleton"][bone.name] = bone_data

	return armature_data

def dump_json(file, data):
	file.write(json.dumps(data, indent="\t", separators=(',',' : ')))

def write_model_data(context, filepath, use_some_setting):
	f = open(filepath, 'w', encoding='utf-8')
	meshes = {}
	for obj in bpy.data.objects:
		if obj.users > 0:
			if obj.type == 'MESH':
				armature = obj.find_armature()
				if armature is not None:
					meshes[obj.name] = mesh_data(obj, anim_data(armature.data))
				else:
					meshes[obj.name] = mesh_data(obj, None)

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
