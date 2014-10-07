import os
import numpy
import math
from __main__ import vtk, qt, ctk, slicer


class PickAndPaint:
    def __init__(self, parent):
        parent.title = "Pick And Paint"
        parent.dependencies = []
        parent.contributors = ["Lucie Macron"]  # replace with "Firstname Lastname (Org)"
        parent.helpText = """
        """
        parent.acknowledgementText = """
        This module was developed by Lucie Macron, University of Michigan
        """
        self.parent = parent


class PickAndPaintWidget:
    def __init__(self, parent=None):
        self.developerMode = True
        if not parent:
            self.parent = slicer.qMRMLWidget()
            self.parent.setLayout(qt.QVBoxLayout())
            self.parent.setMRMLScene(slicer.mrmlScene)
        else:
            self.parent = parent
        self.layout = self.parent.layout()
        if not parent:
            self.setup()
            self.parent.show()

    def setup(self):
        if self.developerMode:
            self.reloadButton = qt.QPushButton("Reload")
            self.reloadButton.toolTip = "Reload this module."
            self.reloadButton.name = "SurfaceToolbox Reload"
            self.layout.addWidget(self.reloadButton)
            self.reloadButton.connect('clicked()', self.onReload)

        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
        self.interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")


        class activeState (object):
            def __init__(self):

                self.inputModelNode = None
                self.outpuModelNode = None
                self.fiducialID = 0
                self.radiusROI = 4
                self.indexClosestPoint = -1


        self.activeState = activeState()

        self.logic = PickAndPaintLogic()

        self.fidNode = slicer.vtkMRMLMarkupsFiducialNode()
        slicer.mrmlScene.AddNode(self.fidNode)

        # ------------------------------------------------------------------------------------
        #                                       Input Selection
        # ------------------------------------------------------------------------------------
        inputModelSelectorFrame = qt.QFrame(self.parent)
        inputModelSelectorFrame.setLayout(qt.QHBoxLayout())
        self.parent.layout().addWidget(inputModelSelectorFrame)

        inputModelSelectorLabel = qt.QLabel("Input Model: ", inputModelSelectorFrame)
        inputModelSelectorLabel.setToolTip("Select the input model")
        inputModelSelectorFrame.layout().addWidget(inputModelSelectorLabel)
        inputModelSelector = slicer.qMRMLNodeComboBox(inputModelSelectorFrame)
        inputModelSelector.nodeTypes = ( ("vtkMRMLModelNode"), "")
        inputModelSelector.selectNodeUponCreation = False
        inputModelSelector.addEnabled = False
        inputModelSelector.removeEnabled = False
        inputModelSelector.noneEnabled = True
        inputModelSelector.showHidden = False
        inputModelSelector.showChildNodeTypes = False
        inputModelSelector.setMRMLScene(slicer.mrmlScene)
        inputModelSelectorFrame.layout().addWidget(inputModelSelector)

        #  ------------------------------------------------------------------------------------
        #                                      Add Fiducials Group
        #  ------------------------------------------------------------------------------------
        # Add Fiducial Button
        addFiducialsButton = qt.QPushButton("Add Fiducials")

        # Find Closest Point Button
        closestPointButton = qt.QPushButton("Find Closest Point")

        # Add Fiducials GroupBox
        addFiducialBox = qt.QGroupBox()
        addFiducialBox.title = "Add Fiducials"
        self.parent.layout().addWidget(addFiducialBox)

        addFiducialsBoxLayout = qt.QVBoxLayout()

        addFiducialsBoxLayout.addWidget(addFiducialsButton)
        addFiducialsBoxLayout.addWidget(closestPointButton)
        addFiducialsBoxLayout.addStretch(1)
        addFiducialBox.setLayout(addFiducialsBoxLayout)

        def onAddButton():
            self.interactionNode.SetCurrentInteractionMode(1)
            print self.fidNode.GetNumberOfFiducials()


        def onFindClosestPoint():
            closestPointButton.text = "Working..."
            closestPointButton.repaint()
            slicer.app.processEvents()
            self.activeState.indexClosestPoint = self.logic.getClosestPointPosition(self.fidNode, self.activeState)
            closestPointButton.text = "Find Closest Point"


        addFiducialsButton.connect('clicked()', onAddButton)
        closestPointButton.connect('clicked()', onFindClosestPoint)

        #  ------------------------------------------------------------------------------------
        #                                               ROI Group
        #  ------------------------------------------------------------------------------------

        # ROI GroupBox
        roiGroupBox = qt.QGroupBox()
        roiGroupBox.title = "Region of interest"
        self.parent.layout().addWidget(roiGroupBox)

        radiusDefinitionWidget = ctk.ctkSliderWidget()
        radiusDefinitionWidget.singleStep = 1.0
        radiusDefinitionWidget.minimum = 1.0
        radiusDefinitionWidget.maximum = 100.0
        radiusDefinitionWidget.value = 0.0

        roiBoxLayout = qt.QFormLayout()
        roiBoxLayout.addRow("Value of radius", radiusDefinitionWidget)
        roiGroupBox.setLayout(roiBoxLayout)

        def onFindNeighbor():
            result = self.logic.getNeighbor(self.activeState)
            if result:
                print "Good Game !!!! =) "
            else:
                print "Try Again =( "

        def updateFunction():
            closestPointButton.enabled = self.activeState.inputModelNode != None
            addFiducialsButton.enabled = self.activeState.inputModelNode != None

        scope_locals = locals()
        def connect(obj, evt, cmd):
            def callback(*args):
                current_locals = scope_locals.copy()
                current_locals.update({'args': args})
                exec cmd in globals(), current_locals
                updateFunction()
            obj.connect(evt, callback)

        connect(inputModelSelector, 'currentNodeChanged(vtkMRMLNode*)', 'self.activeState.inputModelNode = args[0]')
        connect(radiusDefinitionWidget, 'valueChanged(double)', 'self.activeState.radiusROI = args[0]')
        radiusDefinitionWidget.connect('valueChanged(double)', onFindNeighbor)

        self.layout.addStretch(1)
        updateFunction()


    def onReload(self, moduleName="PickAndPaint"):
        """Generic reload method for any scripted module.
        ModuleWizard will subsitute correct default moduleName.
        """
        print " ---------------------RELOAD------------------------ \n"
        globals()[moduleName] = slicer.util.reloadScriptedModule(moduleName)


class PickAndPaintLogic:
    def __init__(self):
        pass

    def paintRenderer(self, mapper, actor):
        actor.SetMapper(mapper)
        # renderer = slicer.app.layoutManager().threeDWidget(0).threeDView().renderWindow().GetRenderers().GetFirstRenderer()
        renderer = slicer.app.layoutManager().activeThreeDRenderer()
        renderer.AddActor(actor)
        renderer.Render()


    def getNeighbor(self, activeState):

        polyData = activeState.inputModelNode.GetPolyData()
        pointData = polyData.GetPointData()
        pointID = activeState.indexClosestPoint
        distance = activeState.radiusROI

        def GetConnectedVertices(polyData, pointID):
            cellList = vtk.vtkIdList()
            idsList = vtk.vtkIdList()

            idsList.InsertNextId(pointID)

            # Get cells that vertex 'pointID' belongs to
            polyData.GetPointCells(pointID, cellList)
            numberOfIds = cellList.GetNumberOfIds()
            
            for i in range(0, numberOfIds):
                # Get points which compose all cells
                pointIdList = vtk.vtkIdList()
                polyData.GetCellPoints(cellList.GetId(i), pointIdList)

                for i in range(0, pointIdList.GetNumberOfIds()):
                    if pointIdList.GetId(i) != pointID:
                        idsList.InsertUniqueId(pointIdList.GetId(i))
            return idsList


        def add2IdLists(list1, list2):
            for i in range(0, list2.GetNumberOfIds()):
                list1.InsertUniqueId(list2.GetId(i))

            return list1

        connectedVerticesList = GetConnectedVertices(polyData, pointID)

        if distance > 1:
            verticesListTemp = vtk.vtkIdList()
            for dist in range(1, int(distance)):
                for el in range(0, connectedVerticesList.GetNumberOfIds()):
                    connectedList = GetConnectedVertices(polyData,
                                                         connectedVerticesList.GetId(el))
                    verticesListTemp = add2IdLists(connectedVerticesList,
                                                   connectedList)
                connectedVerticesList = verticesListTemp


        arrayToAdd = vtk.vtkDoubleArray()
        arrayToAdd.SetName('ROI')
        for i in range(0, polyData.GetNumberOfPoints()):
            arrayToAdd.InsertNextValue(0)

        numberofElements = connectedVerticesList.GetNumberOfIds()
        for i in range(0, numberofElements):
            arrayToAdd.SetValue(connectedVerticesList.GetId(i), 1)

        pointData.SetScalars(arrayToAdd)

        lut = vtk.vtkLookupTable()
        tableSize = 2
        lut.SetNumberOfTableValues(tableSize)
        lut.Build()
        lut.SetTableValue(0, 0, 0, 1, 1)
        lut.SetTableValue(1, 1, 0, 0, 1)

        connectedVertexMapper = vtk.vtkDataSetMapper()
        connectedVertexMapper.SetInputData(polyData)
        connectedVertexMapper.SetScalarRange(0, 1)
        connectedVertexMapper.SetLookupTable(lut)
        connectedVertexMapper.SetScalarVisibility(True)

        connectedVertexActor = vtk.vtkActor()
        connectedVertexActor.GetProperty().SetPointSize(5)

        self.paintRenderer(connectedVertexMapper, connectedVertexActor)

        return True
    
    

    def getClosestPointPosition(self, fidNode, activeState):
        fiducialCoord = numpy.zeros(3)
        fidNode.GetNthFiducialPosition(activeState.fiducialID, fiducialCoord)
        polyData = activeState.inputModelNode.GetPolyData()

        def calculateDistance(p0, p1):
            V = vtk.vtkMath()
            return V.Distance2BetweenPoints(p0, p1)

        numberVertex = polyData.GetNumberOfPoints()
        verticesModel = polyData.GetPoints()
        distanceMin = vtk.vtkMath().Inf()
        for i in range(0, numberVertex):
            coordVerTemp = numpy.zeros(3)
            verticesModel.GetPoint(i, coordVerTemp)
            distance = calculateDistance(fiducialCoord, coordVerTemp)
            if distance < distanceMin:
                distanceMin = distance
                indexClosestPoint = i
        verticesModel.GetPoint(indexClosestPoint, fiducialCoord)

        fidNode.SetNthFiducialPosition(activeState.fiducialID,
                                       fiducialCoord[0],
                                       fiducialCoord[1],
                                       fiducialCoord[2])
        return indexClosestPoint
