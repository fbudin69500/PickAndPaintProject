import os
import numpy
import time, datetime
from __main__ import vtk, qt, ctk, slicer


class PickAndPaint:
    def __init__(self, parent):
        parent.title = "Pick And Paint"
        parent.dependencies = []
        parent.contributors = ["Lucie Macron"]
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
        print " ----- SetUp ------"
        if self.developerMode:
            self.reloadButton = qt.QPushButton("Reload")
            self.reloadButton.toolTip = "Reload this module."
            self.reloadButton.name = "SurfaceToolbox Reload"
            self.layout.addWidget(self.reloadButton)
            self.reloadButton.connect('clicked()', self.onReload)

        class inputState (object):
            def __init__(self):
                self.inputModelNode = None
                self.fidNode = None
                self.PointModifiedEventTag = None
                self.mouvementSurfaceStatus = True
                self.fiducialsID = -1
                self.radiusROI = 0
                self.indexClosestPoint = -1

            def printElement(self):
                print "Input Name: ", self.inputModelNode
                # print "FidNode: ", self.fidNode



        self.logic = PickAndPaintLogic()
        # /!\ create a list, where we put all the different model on it ! /!\
        self.activeInput = None
        self.dictionary = dict()
        self.dictionary.clear()

        self.numOfFiducials = 0

        # ------------------------------------------------------------------------------------
        #                                       Input Selection
        # ------------------------------------------------------------------------------------
        inputModelSelectorFrame = qt.QFrame(self.parent)
        inputModelSelectorFrame.setLayout(qt.QHBoxLayout())
        self.parent.layout().addWidget(inputModelSelectorFrame)

        inputModelSelector = slicer.qMRMLNodeComboBox()
        inputModelSelector.objectName = 'inputFiducialsNodeSelector'
        inputModelSelector.nodeTypes = ['vtkMRMLModelNode']
        inputModelSelector.selectNodeUponCreation = False
        inputModelSelector.addEnabled = False
        inputModelSelector.removeEnabled = False
        inputModelSelector.noneEnabled = True
        inputModelSelector.showHidden = False
        inputModelSelector.showChildNodeTypes = False
        inputModelSelector.setMRMLScene(slicer.mrmlScene)

        inputModelSelectorFrame.layout().addWidget(inputModelSelector)

        #  ------------------------------------------------------------------------------------
        #                                   BUTTONS
        #  ------------------------------------------------------------------------------------

        #  ------------------------------- Add Fiducials Group --------------------------------
        # Add Fiducials GroupBox
        addFiducialBox = qt.QGroupBox()
        addFiducialBox.title = "Add Fiducials"
        self.parent.layout().addWidget(addFiducialBox)

        # Fiducials Scale
        fiducialsScaleWidget = ctk.ctkSliderWidget()
        fiducialsScaleWidget.singleStep = 0.1
        fiducialsScaleWidget.minimum = 0.1
        fiducialsScaleWidget.maximum = 20.0
        fiducialsScaleWidget.value = 2.0
        fiducialsScaleLayout = qt.QFormLayout()
        fiducialsScaleLayout.addRow("Scale: ", fiducialsScaleWidget)

        # Add Fiducials Button
        addFiducialsButton = qt.QPushButton("Add Fiducials")
        addFiducialsButton.enabled = False

        # Movements on the surface
        surfaceDeplacemenCheckBox = qt.QCheckBox(" On Surface ")
        surfaceDeplacemenCheckBox.setChecked(True)

        # Layouts
        scaleAndAddFiducialLayout = qt.QHBoxLayout()
        scaleAndAddFiducialLayout.addWidget(addFiducialsButton)
        scaleAndAddFiducialLayout.addLayout(fiducialsScaleLayout)
        scaleAndAddFiducialLayout.addWidget(surfaceDeplacemenCheckBox)

        # if self.developerMode:
        #     # Find Closest Point Button
        #     closestPointButton = qt.QPushButton("Find Closest Point")
        #     closestPointButton.enabled = False

        addFiducialBoxLayout = qt.QVBoxLayout()
        addFiducialBoxLayout.addLayout(scaleAndAddFiducialLayout)
        addFiducialBox.setLayout(addFiducialBoxLayout)

        #  ----------------------------------- ROI Group ------------------------------------
        # ROI GroupBox
        roiGroupBox = qt.QGroupBox()
        roiGroupBox.title = "Region of interest"
        self.parent.layout().addWidget(roiGroupBox)

        self.radiusDefinitionWidget = ctk.ctkSliderWidget()
        self.radiusDefinitionWidget.singleStep = 1.0
        self.radiusDefinitionWidget.minimum = 1.0
        self.radiusDefinitionWidget.maximum = 100.0
        self.radiusDefinitionWidget.value = 1.0

        roiBoxLayout = qt.QFormLayout()
        roiBoxLayout.addRow("Value of radius", self.radiusDefinitionWidget)
        roiGroupBox.setLayout(roiBoxLayout)
        self.layout.addStretch(1)

        # ------------------------------------------------------------------------------------
        #                                   CONNECTIONS
        # ------------------------------------------------------------------------------------
        def initialize():
            self.activeInput = inputModelSelector.currentNode()

            if self.activeInput != None:
                if not self.dictionary.has_key(self.activeInput.GetName()):
                    self.dictionary[self.activeInput.GetName()] = inputState()

                    # Fiducial Node Definition :
                    self.dictionary[self.activeInput.GetName()].inputModelNode = self.activeInput
                    self.dictionary[self.activeInput.GetName()].fidNode = slicer.vtkMRMLMarkupsFiducialNode()
                    slicer.mrmlScene.AddNode(self.dictionary[self.activeInput.GetName()].fidNode)

                    self.dictionary[self.activeInput.GetName()].PointModifiedEventTag = \
                        self.dictionary[self.activeInput.GetName()].fidNode.AddObserver(self.dictionary[self.activeInput.GetName()].fidNode.PointModifiedEvent,
                                                                                        onPointModifiedEvent)

            # Interaction
            selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
            selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
            self.interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")

            addFiducialsButton.enabled = self.dictionary[self.activeInput.GetName()].inputModelNode != None
            if self.numOfFiducials >= 1:
                addFiducialsButton.enabled = False

            print "Number of Fiducials on Initialize: ", self.numOfFiducials
            # Default value
            fiducialsScaleWidget.value = 2.0
            # radiusDefinitionWidget.value = 1.0


        def onPointModifiedEvent ( obj, event):
            # If a fiducial is added:
            if self.dictionary[self.activeInput.GetName()].fidNode.GetNumberOfMarkups() > self.numOfFiducials:
                self.numOfFiducials += 1
                self.dictionary[self.activeInput.GetName()].fiducialsID = self.dictionary[self.activeInput.GetName()].fiducialsID + 1

                if self.numOfFiducials >= 1:
                    addFiducialsButton.enabled = False

            # remove observer to make sure, the callback function won't be disturbed
            self.dictionary[self.activeInput.GetName()].fidNode.RemoveObserver(self.dictionary[self.activeInput.GetName()].PointModifiedEventTag)
            self.dictionary[self.activeInput.GetName()].fidNode.SetNthFiducialLabel(self.dictionary[self.activeInput.GetName()].fiducialsID,
                                                                                    self.dictionary[self.activeInput.GetName()].inputModelNode.GetName())

            print self.dictionary[self.activeInput.GetName()].fidNode.GetNthFiducialLabel()
            if self.dictionary[self.activeInput.GetName()].mouvementSurfaceStatus:
                self.dictionary[self.activeInput.GetName()].indexClosestPoint = self.logic.getClosestPointIndex(self.dictionary[self.activeInput.GetName()])

            time.sleep(0.08)
            self.dictionary[self.activeInput.GetName()].PointModifiedEventTag = \
                self.dictionary[self.activeInput.GetName()].fidNode.AddObserver(self.dictionary[self.activeInput.GetName()].fidNode.PointModifiedEvent,
                                                                                onPointModifiedEvent)
            # if we move the point, we want the ROI to move with it
            if self.dictionary[self.activeInput.GetName()].radiusROI != 0:
                self.logic.getNeighbor(self.dictionary[self.activeInput.GetName()])

        def onAddButton():
            self.interactionNode.SetCurrentInteractionMode(1)

        def onMarkupsScaleChanged():
            self.dictionary[self.activeInput.GetName()].printElement()
            if self.dictionary[self.activeInput.GetName()].fidNode:
                displayFiducialNode = self.dictionary[self.activeInput.GetName()].fidNode.GetMarkupsDisplayNode()
                print self.dictionary[self.activeInput.GetName()].fidNode.GetNumberOfFiducials()

            disabledModify = displayFiducialNode.StartModify()
            displayFiducialNode.SetGlyphScale(fiducialsScaleWidget.value)
            displayFiducialNode.SetTextScale(fiducialsScaleWidget.value)
            displayFiducialNode.EndModify(disabledModify)

        def onSurfaceDeplacementStateChanged():
            if surfaceDeplacemenCheckBox.isChecked():
                self.dictionary[self.activeInput.GetName()].mouvementSurfaceStatus = True
                self.dictionary[self.activeInput.GetName()].indexClosestPoint = self.logic.getClosestPointIndex(self.dictionary[self.activeInput.GetName()])
            else:
                self.dictionary[self.activeInput.GetName()].mouvementSurfaceStatus = False


        def onRadiusValueChanged():
            self.dictionary[self.activeInput.GetName()].radiusROI = self.radiusDefinitionWidget.value

            if self.dictionary[self.activeInput.GetName()].inputModelNode:
                self.radiusDefinitionWidget.tracking = False
                self.logic.getNeighbor(self.dictionary[self.activeInput.GetName()])
                self.radiusDefinitionWidget.tracking = True

        inputModelSelector.connect('currentNodeChanged(vtkMRMLNode*)', initialize)
        addFiducialsButton.connect('clicked()', onAddButton)
        fiducialsScaleWidget.connect('valueChanged(double)', onMarkupsScaleChanged)
        surfaceDeplacemenCheckBox.connect('stateChanged(int)', onSurfaceDeplacementStateChanged)
        self.radiusDefinitionWidget.connect('valueChanged(double)', onRadiusValueChanged)

        self.layout.addStretch(1)


    def onReload(self, moduleName="PickAndPaint"):
        """Generic reload method for any scripted module.
        ModuleWizard will subsitute correct default moduleName.
        """
        print " --------------------- RELOAD ------------------------ \n"
        globals()[moduleName] = slicer.util.reloadScriptedModule(moduleName)


class PickAndPaintLogic:
    def __init__(self):
        pass

    def getNeighbor(self, activeState):

        displayNode = activeState.inputModelNode.GetDisplayNode()
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
                for i in range(0, connectedVerticesList.GetNumberOfIds()):
                    connectedList = GetConnectedVertices(polyData,
                                                         connectedVerticesList.GetId(i))
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

        lut = vtk.vtkLookupTable()
        tableSize = 2
        lut.SetNumberOfTableValues(tableSize)
        lut.Build()
        lut.SetTableValue(0, 0, 0, 1, 1)
        lut.SetTableValue(1, 1, 0, 0, 1)

        arrayToAdd.SetLookupTable(lut)
        pointData.AddArray(arrayToAdd)

        disabledModify = displayNode.StartModify()
        displayNode.SetScalarVisibility(True)
        displayNode.SetActiveScalarName('ROI')
        displayNode.EndModify(disabledModify)

        # print datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
        # print "         distance: ", distance
        return True

    def getClosestPointIndex(self,  activeState):
        # Each time we add a fiducial, we actually add a Markup which is
        # composed by only one fiducial by default.

        fidNode = activeState.fidNode
        fiducialsID = activeState.fiducialsID
        displayNode = fidNode.GetMarkupsDisplayNode()

        fiducialCoord = numpy.zeros(3)
        fidNode.GetNthFiducialPosition(fiducialsID, fiducialCoord)

        # print fiducialCoord

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

        fiducialCoord2 = numpy.zeros(3)
        fidNode.GetNthFiducialPosition(fiducialsID, fiducialCoord2)
        # print "before process : ", fiducialCoord2

        disabledModify = displayNode.StartModify()
        fidNode.SetNthFiducialPosition(fiducialsID,
                                       fiducialCoord[0],
                                       fiducialCoord[1],
                                       fiducialCoord[2])

        # fidNode.SetMarkupPointFromArray(fiducialsID, 0, fiducialCoord )
        displayNode.EndModify(disabledModify)
        fidNode.GetNthFiducialPosition(fiducialsID, fiducialCoord)
        # print "New coord : ", fiducialCoord

        return indexClosestPoint



