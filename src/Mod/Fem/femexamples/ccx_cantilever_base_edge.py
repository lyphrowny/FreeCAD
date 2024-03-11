# ***************************************************************************
# *   Copyright (c) 2020 Bernd Hahnebach <bernd@bimstatik.org>              *
# *   Copyright (c) 2020 Sudhanshu Dubey <sudhanshu.thethunder@gmail.com    *
# *                                                                         *
# *   This file is part of the FreeCAD CAx development system.              *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2 of     *
# *   the License, or (at your option) any later version.                   *
# *   for detail see the LICENCE text file.                                 *
# *                                                                         *
# *   This program is distributed in the hope that it will be useful,       *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU Library General Public License for more details.                  *
# *                                                                         *
# *   You should have received a copy of the GNU Library General Public     *
# *   License along with this program; if not, write to the Free Software   *
# *   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
# *   USA                                                                   *
# *                                                                         *
# ***************************************************************************

import FreeCAD

import Fem
import ObjectsFem

from .manager import get_meshname
from .manager import init_doc


def create_nodes(femmesh, x, y, z):
    # nodes
    femmesh.addNode(0,0,0,1)
    femmesh.addNode(x,y,z,2)
    femmesh.addNode(x//2, y//2, z//2,3)
    return True


def create_elements(femmesh):
    # elements
    femmesh.addEdge([1, 2,3], 1)
    return True


def setup_cantilever_base_edge(x,y,z,doc=None, solvertype="ccxtools"):

    # init FreeCAD document
    if doc is None:
        doc = init_doc()

    # # geometric objects
    # # load line
    # load_line = doc.addObject("Part::Line", "LoadLine")
    # load_line.X1 = 0
    # load_line.Y1 = 0
    # load_line.Z1 = 10
    # load_line.X2 = 0
    # load_line.Y2 = 0
    # load_line.Z2 = 0

    # cantilever line
    geom_obj = doc.addObject("Part::Line", "CantileverLine")
    geom_obj.X1 = 0
    geom_obj.Y1 = 0
    geom_obj.Z1 = 0
    geom_obj.X2 = x
    geom_obj.Y2 = y
    geom_obj.Z2 = z

    doc.recompute()

    if FreeCAD.GuiUp:
        # load_line.ViewObject.Visibility = False
        geom_obj.ViewObject.Document.activeView().viewAxonometric()
        geom_obj.ViewObject.Document.activeView().fitAll()

    # analysis
    analysis = ObjectsFem.makeAnalysis(doc, "Analysis")

    # solver
    if solvertype == "calculix":
        solver_obj = ObjectsFem.makeSolverCalculix(doc, "SolverCalculiX")
    elif solvertype == "ccxtools":
        solver_obj = ObjectsFem.makeSolverCalculixCcxTools(doc, "CalculiXccxTools")
        solver_obj.WorkingDir = u""
    elif solvertype == "mystran":
        solver_obj = ObjectsFem.makeSolverMystran(doc, "SolverMystran")
    else:
        FreeCAD.Console.PrintWarning(
            "Unknown or unsupported solver type: {}. "
            "No solver object was created.\n".format(solvertype)
        )
    if solvertype == "calculix" or solvertype == "ccxtools":
        solver_obj.AnalysisType = "static"
        solver_obj.GeometricalNonlinearity = "linear"
        solver_obj.ThermoMechSteadyState = False
        solver_obj.MatrixSolverType = "default"
        solver_obj.IterationsControlParameterTimeUse = False
        solver_obj.SplitInputWriter = False
        solver_obj.BeamShellResultOutput3D = True
    analysis.addObject(solver_obj)

    # beam section
    beamsection_obj = ObjectsFem.makeElementGeometry1D(
        doc,
        sectiontype="Rectangular",
        width=1.0,
        height=3.0,
        name="BeamCrossSection"
    )
    analysis.addObject(beamsection_obj)

    rot = ObjectsFem.makeElementRotation1D(doc)
    rot.Rotation = 0
    analysis.addObject(rot)

    # material
    material_obj = ObjectsFem.makeMaterialSolid(doc, "MechanicalMaterial")
    mat = material_obj.Material
    mat["Name"] = "Calculix-Steel"
    mat["YoungsModulus"] = "210000 MPa"
    mat["PoissonRatio"] = "0.30"
    material_obj.Material = mat
    analysis.addObject(material_obj)

    # constraint fixed
    con_fixed = ObjectsFem.makeConstraintFixed(doc, "ConstraintFixed")
    con_fixed.References = [(geom_obj, "Vertex1")]
    analysis.addObject(con_fixed)

    # constraint force
    con_force = ObjectsFem.makeConstraintForce(doc, "ConstraintForce")
    con_force.References = [(geom_obj, "Vertex2")]
    con_force.Force = "1.0 N" # 9 MN
    # con_force.Direction = (load_line, ["Edge1"])
    con_force.Reversed = False
    analysis.addObject(con_force)

    # mesh
    fem_mesh = Fem.FemMesh()
    control = create_nodes(fem_mesh, x, y ,z)
    if not control:
        FreeCAD.Console.PrintError("Error on creating nodes.\n")
    control = create_elements(fem_mesh)
    if not control:
        FreeCAD.Console.PrintError("Error on creating elements.\n")
    femmesh_obj = analysis.addObject(ObjectsFem.makeMeshGmsh(doc, get_meshname()))[0]
    femmesh_obj.FemMesh = fem_mesh
    femmesh_obj.Part = geom_obj
    femmesh_obj.SecondOrderLinear = False
    femmesh_obj.ElementDimension = "1D"
    femmesh_obj.CharacteristicLengthMax = "0.0 mm"
    femmesh_obj.CharacteristicLengthMin = "0.0 mm"

    doc.recompute()
    return doc
