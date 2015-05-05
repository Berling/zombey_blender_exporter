import bpy
import json
import bmesh
from mathutils import Matrix, Quaternion

def mesh_data(obj, anim_data, bone_ids):
	mesh = bmesh.new()
	mesh.from_mesh(obj.data)
	bmesh.ops.triangulate(mesh, faces=mesh.faces)
	name = obj.data.name
	write_skin = False
	vertex_groups = obj.vertex_groups
	dvert_layer = mesh.verts.layers.deform.active

	if dvert_layer is None:
		write_skin = True

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
			vertexattributes["position"] = [pos.x, pos.y, pos.z]
			vertexattributes["texcoord"] = [uv.x, uv.y]
			vertexattributes["normal"] = [nor.x, nor.y, nor.z]
			if vertices.count(vertexattributes) == 0:
				vertices.append(vertexattributes)

			triangle.append(vertices.index(vertexattributes))

			if anim_data is not None and vertex_groups is not None:
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
						index = anim_data["skeleton"][bone_ids[bone_name]]["id"]
						vertexattributes["indices"].append(index)
						vertexattributes["weights"].append(value)

		submeshes[material.name]["indices"].append(triangle)

	meshdata["vertices"] = vertices
	meshdata["submeshes"] = submeshes

	mesh.free()
	del mesh

	modeldata = {}
	modeldata.update(meshdata)
	if anim_data is not None:
		modeldata.update(anim_data)

	return modeldata

def anim_data(armature, bone_ids):
	armature_data = {}
	armature_data["skeleton"] = {}
	ids = 0

	armature_data["bone_hierachy"] = {}
	for i in range(0, len(armature.bones)):
		armature_data["bone_hierachy"][i] = []
	for bone in armature.bones:
		bone_data = {}
		if bone.name not in bone_ids:
			bone_ids[bone.name] = ids
			ids += 1
		bone_data["id"] = bone_ids[bone.name]
		parent = bone.parent
		parent_transformation = Matrix()
		parent_transformation.identity()
		if parent is None:
			bone_data["parent"] = None
		else:
			if parent.name not in bone_ids:
				bone_ids[parent.name] = ids
				ids += 1
			bone_data["parent"] = bone_ids[parent.name]
			parent_transformation = armature.bones[bone_data["parent"]].matrix_local
			armature_data["bone_hierachy"][bone_data["parent"]].append(bone_data["id"])

		transformation = parent_transformation.inverted() * bone.matrix_local
		rot = transformation.to_quaternion()
		rot.normalize()
		bone_data["rotation"] = [rot.w, rot.x, rot.y, rot.z]
		pos = transformation.to_translation()
		bone_data["translation"] = [pos.x, pos.y, pos.z]
		scale = transformation.to_scale()
		bone_data["scale"] = [scale.x, scale.y, scale.z]

		armature_data["skeleton"][bone_ids[bone.name]] = bone_data

	armature_data["animations"] = {}
	for action in bpy.data.actions:
		armature_data["animations"][action.name] = {}
		frame_range = action.frame_range
		armature_data["animations"][action.name]["length"] = frame_range[1] - frame_range[0]
		armature_data["animations"][action.name]["tracks"] = {}
		old_name = ""
		for fcu in action.fcurves:
			bone_name = fcu.data_path
			bone_name = bone_name[12:len(bone_name)]
			bone_name = bone_name[0:bone_name.find("\"")]
			bone_id = bone_ids[bone_name]

			if bone_name not in armature_data["animations"][action.name]["tracks"]:
				armature_data["animations"][action.name]["tracks"][bone_name] = {}
				armature_data["animations"][action.name]["tracks"][bone_name]["id"] = bone_id

			transformation_name = fcu.data_path
			transformation_name = transformation_name[transformation_name.rfind(".") + 1:len(transformation_name)]
			trans = armature_data["animations"][action.name]["tracks"][bone_name]
			if transformation_name not in trans:
				trans[transformation_name] = []

			index = 0
			for keyframe in fcu.keyframe_points:
				if transformation_name != old_name:
					trans[transformation_name].append({});
					trans[transformation_name][-1]["frame"] = keyframe.co.x - frame_range[0]
					trans[transformation_name][-1]["data"] = []

				trans[transformation_name][index]["data"].append(keyframe.co.y)
				index += 1

			old_name = transformation_name

	return armature_data

def dump_json(file, data):
	file.write(json.dumps(data, indent="\t", separators=(',',' : ')))

def write_model_data(context, filepath):
	f = open(filepath, 'w', encoding='utf-8')
	meshes = {}
	for obj in bpy.data.objects:
		if obj.users > 0:
			if obj.type == 'MESH':
				armature = obj.find_armature()
				if armature is not None:
					bone_ids = {}
					meshes[obj.name] = mesh_data(obj, anim_data(armature.data, bone_ids), bone_ids)
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

	def execute(self, context):
		return write_model_data(context, self.filepath)


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
