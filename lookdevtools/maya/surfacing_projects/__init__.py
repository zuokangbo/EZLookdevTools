"""
.. module:: surfacing_projects
   :synopsis: maya surfacing_projects.

.. moduleauthor:: Ezequiel Mastrasso

"""

import os
import sys
import traceback
import random
import logging

import pymel.core as pm
import maya.mel as mel
import maya.cmds as mc

from lookdevtools.ui.libs import *
from lookdevtools.ui import qtutils
from lookdevtools.common.constants import *
from lookdevtools.common import utils
from lookdevtools.maya import maya
from lookdevtools.maya.maya import materials

logger = logging.getLogger(__name__)


def surfacingInit():
    """
    Initialize the scene for surfacing projects.

    Creates the surfacing root, an empty surfacing project
    and object, and runs the validation to create and
    connect the partition

    Returns:
        bool. Valid scene.

    """
    root = create_project_root()
    if not root.members:
        surfacing_project = create_project("project")
        create_object(surfacing_project, "default_object")
    validate_scene()


def create_project_root_node():
    """Create surfacing root node."""
    surfacing_root = pm.createNode(
        "objectSet", name="surfacing_root"
    )
    surfacing_root.setAttr(
        "surfacing_root", "", force=True
    )
    return surfacing_root


def create_project_root():
    """Create projects root if it doesnt exist."""
    if not get_project_root():
        surfacing_root = create_project_root_node()
        return surfacing_root
    else:
        return get_project_root()


def create_project(name=None):
    """
    Creates a surfacing project.
    
    Kwargs:
        name (str): surfacing project name
    
    """
    if not name:
        name = "project"
    surfacing_project = pm.createNode(
        "objectSet", name=name
    )
    surfacing_project.setAttr(
        ATTR_SURFACING_PROJECT, "", force=True
    )
    create_object(surfacing_project)
    get_project_root().add(surfacing_project)
    update_partition()
    return surfacing_project


def create_object(project, name=None):
    """
    Creates a surfacing Object under a given project.

    Args:
        project (PyNode): surfacing project

    Kwargs:
        name (str): surfacing object name
    
    """
    if not name:
        name = "object"
    surfacing_set = pm.createNode(
        "objectSet", name=name
    )
    surfacing_set.setAttr(
        ATTR_SURFACING_OBJECT, "", force=True
    )
    project.add(surfacing_set)


def update_partition():
    """Recreate the partition node, and reconnects to all the surfacing_objects objectSets."""
    partitions = [
        item
        for item in pm.ls(type="partition")
        if item.hasAttr("surfacing_partition")
    ]
    for each in partitions:
        logger.info(
            "disconnecting existing partition: %s" % each
        )
        each.sets.disconnect()
        pm.delete(each)
        logger.info("deleted partition")
    surfacing_partition = pm.createNode(
        "partition", name="surfacing_partition"
    )
    logger.info(
        "partition created: %s" % surfacing_partition
    )
    surfacing_partition.setAttr(
        "surfacing_partition", "", force=True
    )
    for project in get_projects():
        for object in get_objects(project):
            pm.connectAttr(
                "%s.partition" % object,
                surfacing_partition.sets,
                na=True,
            )
            logger.info(
                "partition connected: %s " % object
            )

def get_project_root():
    """
    Get the project root node.

    Returns:
        PyNode. Surfacing root node

    Raises:
       Exception.

    """
    objSetLs = [
        item
        for item in pm.ls(type="objectSet")
        if item.hasAttr("surfacing_root")
    ]
    if len(objSetLs) == 0:
        logger.info(
            "surfacing_root node found, creating one"
        )
        return create_project_root_node()
    elif len(objSetLs) > 1:
        raise Exception(
            "More than 1 surfacing_root node found, clean up your scene"
        )
    return objSetLs[0]


def get_projects():
    """
    Get all surfacing Projects under the root.

    Returns:
        list. surfacing projects PyNodes list.

    """
    objSetLs = [
        item
        for item in pm.ls(type="objectSet")
        if item.hasAttr(ATTR_SURFACING_PROJECT)
    ]
    return objSetLs


def get_project_by_name(name=None):
    """
    Get surfacing Project by name.

    Kwargs:
        name (str): surfacing project name.

    Returns:
        PyNode. Returns first found hit, we are assuming the objectSet name is equal to surfacing_project attr value.

    """
    projects_list = get_projects()
    for each in projects_list:
        if name == each.name():
            return each
    return None


def get_object_by_name(name=None):
    """
    Get surfacing Object by name.

    Kwargs:
        name (str): surfacing object name.

    Returns:
        PyNode. Returns first found hit, we are assuming the objectSet name is equal to surfacing_object attr value.

    """
    projects_list = get_projects()
    for prj in projects_list:
        objs = get_objects(prj)
        for obj in objs:
            if name == obj.name():
                return obj
    return None


def delete_project(project):
    """
    Delete a surfacing_project, and its members.

    Args:
        project (PyNode): surfacing project.
        
    """
    if is_project(project):
        pm.delete(project.members())
        pm.delete(project)


def get_objects(project):
    """
    Get all surfacing Objects under the given surfacing project
    
    Args:
        project (PyNode): surfacing project
    
    """
    if is_project(project):
        return project.members()
    else:
        return []


def is_project(project):
    """
    Check if the node is a surfacing project
    
    Args:
        project (PyNode): surfacing project

    Returns:
        bool. True if it is.
        
    """
    if project.hasAttr(ATTR_SURFACING_PROJECT):
        return True
    else:
        return False


def is_surfacing_object(surfacing_object):
    """
    Check if node is surfacing Object
    
    Args:
        surfacing_object (PyNode): surfacing_object

    """
    if surfacing_object.hasAttr(ATTR_SURFACING_OBJECT):
        return True
    else:
        return False


def remove_invalid_members():
    """
    Pops all not-allowd member types from surfacing projects and objects.

    Only Allowed types:
     objectSets (surfacing_projects) inside the surfacing projects root
     objectSets (surfacing_object) inside surfacing projects
     transforms (that have a mesh) inside surfacing_object     
    """
    project_root = get_project_root()
    for project in project_root.members():
        if (
            not project.type() == "objectSet"
        ):  #TODO (eze) add check for attr
            project_root.removeMembers([project])
    for project in get_projects():
        for object in get_objects(
            project
        ):  #TODO (eze) add check for attr
            if not object.type() == "objectSet":
                project.removeMembers([object])
            else:
                for member in object.members():
                    if not member.type() == "transform":
                        logger.info(
                            "removing invalid member: %s"
                            % member
                        )
                        object.removeMembers([member])
                    elif not member.listRelatives(
                        type="mesh"
                    ):
                        logger.info(
                            "removing invalid member: %s"
                            % member
                        )
                        object.removeMembers([member])


def get_mesh_transforms(object_list):
    """
    Get all the mesh shapes transforms.

    Includes all descendants in hierarchy.

    Args:
        object_list (list): PyNode list of nodes.

    """
    shapes_in_hierarchy = pm.listRelatives(
        object_list,
        allDescendents=True,
        path=True,
        f=True,
        type="mesh",
    )
    shapes_transforms = pm.listRelatives(
        shapes_in_hierarchy, p=True, path=True, f=True
    )
    return shapes_transforms


def add_member(surfacing_object, transform):
    """
    Add transform to surfacing Object
    
    Args:
        surfacing_object (PyNode): surfacing object
        transform (PyNode): transform node

    """
    pm.sets(surfacing_object, transform, fe=True)


def add_mesh_transforms_to_object(
    surfacing_object, object_list
):
    """
    Add all mesh shape transforms -and descendants- from the list to a surfacing Object.
    
    Args:
        surfacing_object (PyNode): surfacing object
        object_list (list): object list

    """
    pm.select()
    if is_surfacing_object(surfacing_object):
        for item in object_list:
            for transform in get_mesh_transforms(item):
                pm.select(transform)
                add_member(surfacing_object, transform)


def remove_invalid_characters():
    """Remove not allowed characters from surfacing projects and names like '_'."""
    project_root = get_project_root()
    surfacing_projects = get_projects()
    invalid_character = '_'
    for project in surfacing_projects:
        if invalid_character in project.name():
            project.rename(project.name().replace(invalid_character, ''))
            logger.info(
                'Invalid character removed from surfacing_project, new name: %s' % project)
        for surfacing_object in get_objects(project):
            if invalid_character in surfacing_object.name():
                surfacing_object.rename(
                    surfacing_object.name().replace(invalid_character, ''))
                logger.info(
                    'Invalid characters removed from surfacing_object, new name: %s' % surfacing_object)

def validate_scene():
    """
    Validate the scene.
    
    Removes invalidad characters and members, updates the partition, and mesh attributes.

    """
    remove_invalid_characters()
    remove_invalid_members()
    update_partition()
    update_mesh_attributes()

def abc_export(geo_list, file_path):
    """
    Export alembic file from the object list.
    
    Args:
        geo_list (list): list of geometry to export
        file_path (str): export file path

    """
    if geo_list and file_path:
        roots = " -root |" + " -root |".join(
            [str(x) for x in geo_list]
        )
        mel_cmd = (
            r'AbcExport -j "-frameRange 0 0 -uvWrite -dataFormat ogawa -attrPrefix surfacing '
            + roots
            + " -file "
            + (file_path + '"')
        )
        mel.eval(mel_cmd)
        logger.info(
            "Succesful Alembic export to: %s" % file_path
        )

def export_project(project, single_export=True, folder_path=False):
    """
    Export surfacing Project to Alembic.
    
    Args:
        project (PyNode): surfacing project
    
    Kwargs:
        single_export (bool): is single export
        folder_path (str): Export folder path

    """
    current_file = pm.sceneName()
    if single_export:
        check_scene_state()
    if not folder_path:
        folder_path = qtutils.get_folder_path()
    project_geo_list = []
    if utils.is_directory(folder_path) and is_project(project):
        for each in get_objects(project):
            merged_geo = merge_surfacing_object(each)
            if merged_geo:
                project_geo_list.append(merged_geo)
        if project_geo_list:
            if SURFACING_SUBDIV_ITERATIONS:
                for geo in project_geo_list:
                    logger.info(
                        "subdivision level: %s" % SURFACING_SUBDIV_ITERATIONS
                    )
                    logger.info(
                        "subdividing merged members: %s"
                        % geo
                    )
                    # -mth 0 -sdt 2 -ovb 1 -ofb 3 -ofc 0 -ost 0 -ocr 0 -dv 3 -bnr 1 -c 1 -kb 1
                    # -ksb 1 -khe 0 -kt 1 -kmb 1 -suv 1 -peh 0 -sl 1 -dpe 1 -ps 0.1 -ro 1 -ch 1
                    pm.polySmooth(
                        geo, mth=0, sdt=2, ovb=1, dv=SURFACING_SUBDIV_ITERATIONS
                    )
            export_file_path = os.path.join(
                folder_path, str(project) + ".abc"
            )
            abc_export(project_geo_list, export_file_path)
            export_surfacing_object_dir = os.path.join(
                folder_path, str(project)
            )
            utils.create_directoy(export_surfacing_object_dir)
            for geo in project_geo_list:
                export_root = " -root |" + geo
                export_surfacing_object_path = os.path.join(
                    export_surfacing_object_dir
                    + "/"
                    + geo
                    + ".abc"
                )
                abc_export(
                    [geo], export_surfacing_object_path
                )

    if single_export:
        pm.openFile(current_file, force=True)


def merge_surfacing_object(surfacing_object):
    """
    Merge all the meshs assigned to a surfacing Object.
    
    Args:
        surfacing_object (PyNode): surfacing object
    
    Raises:
        BaseException. Could not merge member meshes.

    """
    #TODO (eze) what if there is a single mesh in the surfacing object!
    try:
        members = surfacing_object.members()
        logger.info("Merging members: %s" % members)
        geo_name = "%s_geo" % str(surfacing_object)
        if len(members) > 1:
            geo = pm.polyUnite(*members, n=geo_name)
            return geo[0]
        else:
            logger.info(
                "single object found, skipping merge: %s"
                % members[0]
            )
            members[0].rename(geo_name)
            pm.parent(members[0], world=True)
            return members[0]
    except BaseException:
        logger.error(
            "Could not merge members of: %s"
            % surfacing_object
        )
        return False


def export_all_projects(folder_path=None):
    """
    Export all surfacing Projects.
    
    Kwargs:
        folder_path (str): folder to export files.

    """
    check_scene_state()
    if not folder_path:
        folder_path = qtutils.get_folder_path()
    current_file = pm.sceneName()
    for project in get_projects():
        export_project(
            project, single_export=False, folder_path=folder_path
        )
    pm.openFile(current_file, force=True)
    return True


def check_scene_state():
    """Check the scene state, if modified, will ask the user to save it."""
    if maya.unsaved_scene():
        if maya.save_scene_dialog():
            pm.saveFile(force=True)
        else:
            raise ValueError("Unsaved changes")


def update_mesh_attributes():
    """
    Create attributes on meshes, to reflect the surfacing object they are assinged to.

    Adds the attributes to all the shapes transforms assigned to surfacing Objects
    This will be used later for quick shader/material creation and assignment.
    
    """
    for project in get_projects():
        project.setAttr(ATTR_SURFACING_PROJECT, project)
        logger.info(
            "Updating attributes for project: %s" % project
        )
        for surfacing_object_set in get_objects(project):
            logger.info(
                "\tUpdating attributes for object texture set: %s"
                % surfacing_object_set
            )
            surfacing_object_set.setAttr(
                ATTR_SURFACING_OBJECT, surfacing_object_set
            )
            members = surfacing_object_set.members()
            logger.info(
                "\t\tUpdating attr for meshes: %s" % members
            )
            for member in members:
                member.setAttr(
                    ATTR_SURFACING_PROJECT,
                    project.name(),
                    force=True,
                )
                member.setAttr(
                    ATTR_SURFACING_OBJECT,
                    surfacing_object_set.name(),
                    force=True,
                )


def import_textures(parsed_files=None, key=None, shaders=None):
    """
    Import textures to surfacing objects or projects.
    
    Kwargs:
        parsed_files (list): list of lucidity parsed files with a 'filepath' key
        key (str): surfacing attribute to use for import, surfacing_project or surfacing object
        shaders (list): a list of shaders, where the keys match the parsed files key to use for import    
    
    """
    for parsed_file in parsed_files:
        if parsed_file[key]:
            logger.info('creating material for %s' % parsed_file[key])
            if parsed_file['shader_plug']:
                logger.info('Importing element %s to objectSet %s' % (
                    parsed_file['textureset_element'], parsed_file[key]))
                # create file_node
                file_node = materials.create_file_node(
                    name='surfProj_%s_file' % parsed_file[key])
                # set file_node file path and udim
                file_node.fileTextureName.set(parsed_file['filepath'])
                file_node.uvTilingMode.set(3)
                # do colorspace here
                if 'rgb' in parsed_file['colorspace'].lower():
                    file_node.colorSpace.set("sRGB")
                # try outColor, if fails fall back to outAlpha
                # might need to map out connector in config
                try:
                    file_node.outColor.connect('%s.%s' % (
                        shaders[parsed_file[key]], parsed_file['shader_plug']))
                except BaseException:
                    logger.info('Could not connect outColor to shader')
                try:
                    file_node.outAlpha.connect('%s.%s' % (
                        shaders[parsed_file[key]], parsed_file['shader_plug']))
                except BaseException:
                    logger.error('Could not outAlpha to shader')
                # get surfacing project
                # assign shading_group to surfacig_project
        else:
            logger.info('Skipping %s, no shader plug or project to assign' %
                        parsed_file['textureset_element'])


def create_surfacing_shaders(parsed_files=None, key=None):
    """
    Create shaders and shading groups.
    
    Kwargs:
        parsed_files (list): list of lucidity parsed files with a 'filepath' key
        key (str): surfacing attribute to use for import, surfacing_project or surfacing object
        
    Returns:
        dict. A Dict of PxrSurface shaders matching the key values"""
    shaders = {}
    for prj in utils.get_unique_key_values(parsed_files, key):
        # create material and shading group and assign it
        PxrSurface, shading_group = pm.createSurfaceShader('PxrSurface')
        if key == 'maya_prj':
            prj_set = get_project_by_name(prj)
        elif key == 'maya_obj':
            prj_set = get_object_by_name(prj)
        pm.select(prj_set)
        meshes = pm.ls(sl=True)
        pm.sets(shading_group, forceElement=meshes)
        pm.select(None)
        shaders[prj] = PxrSurface
    return shaders
