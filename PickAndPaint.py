import vtk, qt, ctk, slicer
import numpy
import time

class PickAndPaint:
    def __init__(self, parent):
        parent.title = "Pick 'n Paint "
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
            self.reloadButton.toolTip = "Reload this module"
            self.reloadButton.name = "SurfaceToolbox Reload"
            self.layout.addWidget(self.reloadButton)
            self.reloadButton.connect('clicked()', self.onReload)

        class fiducialState(object):
            def __init__(self):
                self.fiducialLabel = None
                self.inputAssociated = None
                self.fiducialScale = 2.0
                self.radiusROI = 1.0
                self.indexClosestPoint = -1
                self.arrayName = None
                self.listIDFidPropagation = list()
                self.mouvementSurfaceStatus = True

                

            def printElements(self):
                for i in range(0, self.listPropagatedFiducial.__len__()):
                    print "inputAssociated = ", self.listPropagatedFiducial[i].inputAssociated.GetName()
                    print "indexClosestPoint = ", self.listPropagatedFiducial[i].indexClosestPoint
                    print "radius =", self.listPropagatedFiducial[i].radiusROI


        class inputState (object):
            def __init__(self):
                self.inputModelNode = None
                self.listIDFiducial = list()

        # ------------------------------------------------------------------------------------
        #                                   Global Variables
        # ------------------------------------------------------------------------------------
        self.logic = PickAndPaintLogic()

        self.dictionaryInput = dict()
        self.dictionaryInput.clear()
        self.dictionaryFiducial = dict()
        self.dictionaryFiducial.clear()

        self.activeDictionaryInputKey = None
        self.activeInput = None

        self.linkRegion = True

        self.onPropagation = False
        self.fidAdded = False
        self.listModelPropagation = list()

        #-------------------------------------------------------------------------------------
        self.fidNode = slicer.vtkMRMLMarkupsFiducialNode()
        slicer.mrmlScene.AddNode(self.fidNode)

        # Interaction with 3D Scene
        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
        self.interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")

        #-------------------------------------------------------------------------------------
        # ------------------------------------------------------------------------------------
        #                                    Input Selection
        # ------------------------------------------------------------------------------------
        inputLabel = qt.QLabel("Model of Reference: ")

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

        inputModelSelectorFrame = qt.QFrame(self.parent)
        inputModelSelectorFrame.setLayout(qt.QHBoxLayout())
        # self.parent.layout().addWidget(inputModelSelectorFrame)
        inputModelSelectorFrame.layout().addWidget(inputLabel)
        inputModelSelectorFrame.layout().addWidget(inputModelSelector)

        #  ------------------------------------------------------------------------------------
        #                                   BUTTONS
        #  ------------------------------------------------------------------------------------
        #  ------------------------------- Add Fiducials Group --------------------------------
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
        # addFiducialsButton = qt.QPushButton()
        # addFiducialsButton.setIcon(qt.QIcon("/home/luciemac/Desktop/Code/test_moreFiducials/Icons/Fiducials.png"))
        addFiducialsButton.enabled = False

        # Movements on the surface
        surfaceDeplacementCheckBox = qt.QCheckBox("On Surface")
        surfaceDeplacementCheckBox.setChecked(True)

        # Layouts
        scaleAndAddFiducialLayout = qt.QHBoxLayout()
        scaleAndAddFiducialLayout.addWidget(addFiducialsButton)
        scaleAndAddFiducialLayout.addLayout(fiducialsScaleLayout)
        scaleAndAddFiducialLayout.addWidget(surfaceDeplacementCheckBox)

        # Add Fiducials GroupBox
        addFiducialBox = qt.QGroupBox()
        addFiducialBox.title = "Add Fiducials"
        # self.parent.layout().addWidget(addFiducialBox)
        addFiducialBox.setLayout(scaleAndAddFiducialLayout)

        #  ----------------------------------- ROI Group ------------------------------------
        # ROI GroupBox
        roiGroupBox = qt.QGroupBox()
        roiGroupBox.title = "Region of interest"
        # self.parent.layout().addWidget(roiGroupBox)

        self.fiducialComboBoxROI = qt.QComboBox()

        self.radiusDefinitionWidget = ctk.ctkSliderWidget()
        self.radiusDefinitionWidget.singleStep = 1.0
        self.radiusDefinitionWidget.minimum = 1.0
        self.radiusDefinitionWidget.maximum = 20.0
        self.radiusDefinitionWidget.value = 1.0
        self.radiusDefinitionWidget.tracking = False

        roiBoxLayout = qt.QFormLayout()
        roiBoxLayout.addRow("Select a Fiducial:", self.fiducialComboBoxROI)
        roiBoxLayout.addRow("Value of radius", self.radiusDefinitionWidget)
        roiGroupBox.setLayout(roiBoxLayout)


        self.ROICollapsibleButton = ctk.ctkCollapsibleButton()
        self.ROICollapsibleButton.setText("Selection Region of Interest: ")
        self.parent.layout().addWidget(self.ROICollapsibleButton)

        ROICollapsibleButtonLayout = qt.QVBoxLayout()
        ROICollapsibleButtonLayout.addWidget(inputModelSelectorFrame)
        ROICollapsibleButtonLayout.addWidget(addFiducialBox)
        ROICollapsibleButtonLayout.addWidget(roiGroupBox)
        self.ROICollapsibleButton.setLayout(ROICollapsibleButtonLayout)

        self.ROICollapsibleButton.checked = True
        self.ROICollapsibleButton.enabled = True

        #  ----------------------------- Propagate Button ----------------------------------
        self.propagationCollapsibleButton = ctk.ctkCollapsibleButton()
        self.propagationCollapsibleButton.setText(" Propagation: ")
        self.parent.layout().addWidget(self.propagationCollapsibleButton)


        self.propagationInputComboBox = slicer.qMRMLCheckableNodeComboBox()
        self.propagationInputComboBox.nodeTypes = ['vtkMRMLModelNode']
        self.propagationInputComboBox.setMRMLScene(slicer.mrmlScene)

        self.fiducialPropagationComboBox = qt.QComboBox()

        propagateButton = qt.QPushButton("Propagate")
        propagateButton.enabled = True
        linkCheckBox = qt.QCheckBox("Link Region")
        linkCheckBox.setChecked(True)

        propAndLinkLayout = qt.QHBoxLayout()
        propAndLinkLayout.addWidget(propagateButton)
        propAndLinkLayout.addWidget(linkCheckBox)

        propagationBoxLayout = qt.QVBoxLayout()
        propagationBoxLayout.addWidget(self.propagationInputComboBox)
        propagationBoxLayout.addWidget(self.fiducialPropagationComboBox)
        propagationBoxLayout.addLayout(propAndLinkLayout)
        # propagationBoxLayout.addWidget(propagateButton)

        self.propagationCollapsibleButton.setLayout(propagationBoxLayout)
        self.propagationCollapsibleButton.checked = False
        self.propagationCollapsibleButton.enabled = True

        self.layout.addStretch(1)
        # ------------------------------------------------------------------------------------
        #                                   CONNECTIONS
        # ------------------------------------------------------------------------------------
        def onCurrentNodeChanged():
            print " ---- onCurrentNodeChanged ----"
            self.activeInput = inputModelSelector.currentNode()
            if self.activeInput:
                if not self.dictionaryInput.has_key(self.activeInput.GetName()):
                    self.dictionaryInput[self.activeInput.GetName()] = inputState()
                    self.dictionaryInput[self.activeInput.GetName()].inputModelNode = self.activeInput
                self.activeDictionaryInputKey = self.dictionaryInput[self.activeInput.GetName()]

                for keyInput, valueInput in self.dictionaryInput.iteritems():
                    if keyInput != self.activeInput.GetName():
                        if valueInput.listIDFiducial is not None:
                            for id in valueInput.listIDFiducial:
                                self.fidNode.SetNthFiducialVisibility(id, False)

                    else:
                        for id in valueInput.listIDFiducial:
                            self.fidNode.SetNthFiducialVisibility(id, True)
            else:
                print " Input chosen: None! "

            self.fiducialComboBoxROI.clear()
            self.fiducialPropagationComboBox.clear()
            if self.activeDictionaryInputKey.listIDFiducial != None:
                if self.fiducialComboBoxROI.count == 0:
                    for id in self.activeDictionaryInputKey.listIDFiducial:
                        self.fiducialComboBoxROI.addItem(self.fidNode.GetNthFiducialLabel(id))
                        self.fiducialPropagationComboBox.addItem(self.dictionaryFiducial[id].fiducialLabel)
            addFiducialsButton.enabled = self.activeInput != None

        def UpdateInterface():
            print " ---- OnUpdateInterface() -----"
            selectedFidReflID = findIDFromLabel(self.fiducialComboBoxROI.currentText)
            if self.activeInput:
                if self.activeDictionaryInputKey.listIDFiducial :
                    fiducialsScaleWidget.value = self.dictionaryFiducial[self.activeDictionaryInputKey.listIDFiducial[0]].fiducialScale
                    if selectedFidReflID != -1:
                        self.radiusDefinitionWidget.value = self.dictionaryFiducial[selectedFidReflID].radiusROI
                        if self.dictionaryFiducial[selectedFidReflID].mouvementSurfaceStatus:
                            surfaceDeplacementCheckBox.setChecked(True)
                        else :
                            surfaceDeplacementCheckBox.setChecked(False)
                else:
                    self.radiusDefinitionWidget.value = 1.0

        def findIDFromLabel( fiducialLabel ):
            fiducialID = -1
            if self.activeDictionaryInputKey.listIDFiducial != None:
                for id in self.activeDictionaryInputKey.listIDFiducial:
                    print " Id = ", id
                    if self.dictionaryFiducial[id].fiducialLabel == fiducialLabel:
                        fiducialID = id
            return fiducialID

        def onFiducialComboBoxROIChanged():
            print "-------- ComboBox changement --------"
            UpdateInterface()

        def onAddButton():
            self.interactionNode.SetCurrentInteractionMode(1)
            UpdateInterface()

        def onFiducialsScaleChanged():
            print " onFiducialsScaleChanged "
            if self.activeInput:
                for id in self.activeDictionaryInputKey.listIDFiducial:
                    self.dictionaryFiducial[id].fiducialScale = fiducialsScaleWidget.value
                if self.fidNode:
                    displayFiducialNode = self.fidNode.GetMarkupsDisplayNode()
                    disabledModify = displayFiducialNode.StartModify()
                    displayFiducialNode.SetGlyphScale(fiducialsScaleWidget.value)
                    displayFiducialNode.SetTextScale(fiducialsScaleWidget.value)
                    displayFiducialNode.EndModify(disabledModify)
                else:
                    print "Error with fiducialNode"

        def onSurfaceDeplacementStateChanged():
            print  " onSurfaceDeplacementStateChanged "
            selectedFidReflID = findIDFromLabel(self.fiducialComboBoxROI.currentText)
            if self.activeInput:
                if surfaceDeplacementCheckBox.isChecked():
                    self.dictionaryFiducial[selectedFidReflID].mouvementSurfaceStatus = True
                    for id in self.activeDictionaryInputKey.listIDFiducial:
                        self.dictionaryFiducial[id].indexClosestPoint = \
                            self.logic.getClosestPointIndex(self.fidNode,
                                                            self.dictionaryFiducial[id].inputAssociated,
                                                            id)
                else:
                    self.dictionaryFiducial[selectedFidReflID].mouvementSurfaceStatus = False

        def onRadiusValueIsChanging():
            print " -------------------------- onRadiusValueIsChanging -----------------------------"

        def onRadiusValueChanged():
            print " onRadiusValueChanged "
            selectedFidReflID = findIDFromLabel(self.fiducialComboBoxROI.currentText)
            if selectedFidReflID != -1:
                self.dictionaryFiducial[selectedFidReflID].radiusROI = self.radiusDefinitionWidget.value
                if self.activeDictionaryInputKey:
                    if not self.dictionaryFiducial[selectedFidReflID].mouvementSurfaceStatus:
                        surfaceDeplacementCheckBox.setChecked(True)
                        self.dictionaryFiducial[selectedFidReflID].mouvementSurfaceStatus = True

                    self.radiusDefinitionWidget.setEnabled(False)
                    self.logic.getNeighbor(self.dictionaryFiducial[selectedFidReflID])
                    self.radiusDefinitionWidget.setEnabled(True)

                    if self.dictionaryFiducial[selectedFidReflID].listIDFidPropagation != None:
                        for id in self.dictionaryFiducial[selectedFidReflID].listIDFidPropagation:
                            self.dictionaryFiducial[id].radiusROI = self.radiusDefinitionWidget.value
                            self.logic.getNeighbor(self.dictionaryFiducial[id])
            self.radiusDefinitionWidget.tracking = False
            UpdateInterface()

        def onPropagationInputComboBoxCheckedNodesChanged():
            if self.activeInput:
                self.listModelPropagation = self.propagationInputComboBox.checkedNodes()

        def onPropagateButton():
            self.onPropagation = True
            fiducialToPropagateID = findIDFromLabel(self.fiducialPropagationComboBox.currentText)
            listFiducialProp = self.dictionaryFiducial[fiducialToPropagateID].listIDFidPropagation
            if self.listModelPropagation != None:
                for model in self.listModelPropagation:
                    if model.GetName() != self.activeInput.GetName():
                        boolAlreadyExist = False
                        print "listFiducialProp : ", listFiducialProp
                        if listFiducialProp != None:
                            for fidPropId in listFiducialProp:
                                print "     inputAssociated:", self.dictionaryFiducial[fidPropId].inputAssociated.GetName()
                                print "     model.GetName():", model.GetName()
                                if self.dictionaryFiducial[fidPropId].inputAssociated.GetName() == model.GetName():
                                    boolAlreadyExist = True
                                    fidID = fidPropId
                            print "boolAlreadyExist", boolAlreadyExist
                            if  boolAlreadyExist:
                                print " TEST TEST TEST "
                                fidCoord = numpy.zeros(3)
                                self.fidNode.GetNthFiducialPosition(fiducialToPropagateID, fidCoord)
                                self.fidNode.SetNthFiducialPosition(fidID,
                                                                    fidCoord[0],
                                                                    fidCoord[1],
                                                                    fidCoord[2])
                                self.dictionaryFiducial[fidID].indexClosestPoint = \
                                    self.logic.getClosestPointIndex(self.fidNode, self.dictionaryFiducial[fidID].inputAssociated, fidID)
                                print "BEFORE"
                                self.logic.getNeighbor(self.dictionaryFiducial[fidID])
                                print "AFTER"
                            else:
                                fiducialToAddState = fiducialState()
                                fiducialToAddState.inputAssociated = model
                                self.logic.propagateFiducial(self.fidNode,
                                                             fiducialToPropagateID,
                                                             self.dictionaryFiducial[fiducialToPropagateID],
                                                             fiducialToAddState,
                                                             model)
                                self.logic.getNeighbor(fiducialToAddState)
                                self.dictionaryFiducial[self.fidNode.GetNumberOfMarkups() - 1] = fiducialToAddState
                                self.dictionaryFiducial[fiducialToPropagateID].listIDFidPropagation.append(self.fidNode.GetNumberOfMarkups() - 1)
                        else:
                            fiducialToAddState = fiducialState()
                            fiducialToAddState.inputAssociated = model
                            self.logic.propagateFiducial(self.fidNode,
                                                         fiducialToPropagateID,
                                                         self.dictionaryFiducial[fiducialToPropagateID],
                                                         fiducialToAddState,
                                                         model)
                            self.logic.getNeighbor(fiducialToAddState)
                            self.dictionaryFiducial[self.fidNode.GetNumberOfMarkups() - 1] = fiducialToAddState
                            self.dictionaryFiducial[fiducialToPropagateID].listIDFidPropagation.append(self.fidNode.GetNumberOfMarkups() - 1)

            self.onPropagation = False

        def onLinkCheckBoxStateChanged():
            if linkCheckBox.isChecked():
                self.linkRegion = True
                selectedFidID = findIDFromLabel(self.fiducialPropagationComboBox.currentText)
                if self.dictionaryFiducial[selectedFidID].listIDFidPropagation != None :
                    fidCoord = numpy.zeros(3)
                    self.fidNode.GetNthFiducialPosition(selectedFidID, fidCoord)
                    for id in self.dictionaryFiducial[selectedFidID].listIDFidPropagation:
                        self.fidNode.SetNthFiducialPosition(id,
                                                            fidCoord[0],
                                                            fidCoord[1],
                                                            fidCoord[2])
                        self.dictionaryFiducial[id].indexClosestPoint = self.logic.getClosestPointIndex(self.fidNode,
                                                                                                        self.dictionaryFiducial[id].inputAssociated,
                                                                                                        id)
            else:
                self.linkRegion = False

        inputModelSelector.connect('currentNodeChanged(vtkMRMLNode*)', onCurrentNodeChanged)
        addFiducialsButton.connect('clicked()', onAddButton)
        fiducialsScaleWidget.connect('valueChanged(double)', onFiducialsScaleChanged)
        surfaceDeplacementCheckBox.connect('stateChanged(int)', onSurfaceDeplacementStateChanged)
        self.fiducialComboBoxROI.connect('currentIndexChanged(QString)', onFiducialComboBoxROIChanged)
        self.radiusDefinitionWidget.connect('valueChanged(double)', onRadiusValueChanged)
        self.radiusDefinitionWidget.connect('valueIsChanging(double)', onRadiusValueIsChanging)
        self.propagationInputComboBox.connect('checkedNodesChanged()', onPropagationInputComboBoxCheckedNodesChanged)
        propagateButton.connect('clicked()', onPropagateButton)
        linkCheckBox.connect('stateChanged(int)', onLinkCheckBoxStateChanged)

        # ------------------------------------------------------------------------------------
        #                                   OBSERVERS
        # ------------------------------------------------------------------------------------
        def onMarkupAddedEvent (obj, event):
            print " ---- onMarkupAddedEvent ----"
            # print " OBJET : ", obj
            if self.onPropagation == False :
                print " Number of Fiducial ", self.fidNode.GetNumberOfMarkups()
                self.activeDictionaryInputKey.listIDFiducial.append(self.fidNode.GetNumberOfMarkups() - 1)
                listLength = self.activeDictionaryInputKey.listIDFiducial.__len__()

                self.dictionaryFiducial[self.fidNode.GetNumberOfMarkups() - 1] = fiducialState()
                self.dictionaryFiducial[self.fidNode.GetNumberOfMarkups() - 1].inputAssociated = self.activeInput

                fiducialLabel = self.activeDictionaryInputKey.inputModelNode.GetName()+'_'+str(listLength)
                self.dictionaryFiducial[self.fidNode.GetNumberOfMarkups() - 1].fiducialLabel = fiducialLabel

                self.fidNode.SetNthFiducialLabel(self.activeDictionaryInputKey.listIDFiducial[listLength-1],
                                                 fiducialLabel)
                arrayName = self.dictionaryFiducial[self.fidNode.GetNumberOfMarkups() - 1].fiducialLabel + "_ROI"
                self.dictionaryFiducial[self.fidNode.GetNumberOfMarkups() - 1].arrayName = arrayName

                self.fiducialComboBoxROI.addItem(fiducialLabel)
                self.fiducialPropagationComboBox.addItem(fiducialLabel)
                UpdateInterface()

            else:
                print "fiducial added because of propagation"

        def onPointModifiedEvent ( obj, event):
            print " ------ onPointModifiedEvent ------ "
            # remove observer to make sure, the callback function won't be disturbed
            self.fidNode.RemoveObserver(self.PointModifiedEventTag)
            print "self.linkRegion: " , self.linkRegion
            if self.linkRegion:
                i = 0
                for key, value in self.dictionaryFiducial.iteritems():
                    if value.mouvementSurfaceStatus:
                       value.indexClosestPoint =  self.logic.getClosestPointIndex(self.fidNode,
                                                                                  value.inputAssociated,
                                                                                  key)
                    if value.radiusROI >= 1:
                        self.logic.getNeighbor(value)

                    if value.listIDFidPropagation != None :
                        fidCoord = numpy.zeros(3)
                        self.fidNode.GetNthFiducialPosition(key, fidCoord)
                        for id in value.listIDFidPropagation:
                            self.fidNode.SetNthFiducialPosition(id,
                                                                fidCoord[0],
                                                                fidCoord[1],
                                                                fidCoord[2])
                            self.dictionaryFiducial[id].indexClosestPoint = self.logic.getClosestPointIndex(self.fidNode,
                                                                                                            self.dictionaryFiducial[id].inputAssociated,
                                                                                                            id)
                    time.sleep(0.05)
                    i += 1
            else:
                i = 0
                for key, value in self.dictionaryFiducial.iteritems():
                    if value.mouvementSurfaceStatus:
                       value.indexClosestPoint =  self.logic.getClosestPointIndex(self.fidNode,
                                                                                  value.inputAssociated,
                                                                                  key)
                    if value.radiusROI >= 1:
                        self.logic.getNeighbor(value)

                    time.sleep(0.05)
                    i += 1

            self.PointModifiedEventTag = self.fidNode.AddObserver(self.fidNode.PointModifiedEvent,
                                                                  onPointModifiedEvent)

        def onCloseScene(obj, event):
            print " --- OnCloseScene ---"
            # initialize Parameters
            globals()["PickAndPaint"] = slicer.util.reloadScriptedModule("PickAndPaint")

        self.PointModifiedEventTag = self.fidNode.AddObserver(self.fidNode.PointModifiedEvent, onPointModifiedEvent)
        self.MarkupAddedEventTag = self.fidNode.AddObserver(self.fidNode.MarkupAddedEvent, onMarkupAddedEvent)

        slicer.mrmlScene.AddObserver(slicer.mrmlScene.EndCloseEvent, onCloseScene)

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

    def getClosestPointIndex(self, fidNode,  input, fiducialID):
        displayNode = fidNode.GetMarkupsDisplayNode()
        fiducialCoord = numpy.zeros(3)
        fidNode.GetNthFiducialPosition(fiducialID, fiducialCoord)

        polyData = input.GetPolyData()

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
        fidNode.GetNthFiducialPosition(fiducialID, fiducialCoord2)

        disabledModify = displayNode.StartModify()
        fidNode.SetNthFiducialPosition(fiducialID,
                                       fiducialCoord[0],
                                       fiducialCoord[1],
                                       fiducialCoord[2])

        displayNode.EndModify(disabledModify)
        fidNode.GetNthFiducialPosition(fiducialID, fiducialCoord)

        return indexClosestPoint

    def displayROI(self, inputModelNode, scalarName):
        displayNode = inputModelNode.GetModelDisplayNode()
        disabledModify = displayNode.StartModify()
        displayNode.SetScalarVisibility(True)
        displayNode.SetActiveScalarName(scalarName)
        displayNode.EndModify(disabledModify)

    def findArray(self, pointData, arrayName):
        arrayID = -1
        if pointData.HasArray(arrayName) == 1:
            for i in range(0, pointData.GetNumberOfArrays()):
                if pointData.GetArrayName(i) == arrayName:
                    arrayID = i
        return arrayID

    def addArray(self, connectedIdList, inputModelNode, arrayName):
        polyData = inputModelNode.GetPolyData()
        pointData = polyData.GetPointData()
        numberofIds = connectedIdList.GetNumberOfIds()
        # arrayName = 'ROI'
        arrayID = self.findArray( pointData, arrayName)

        if arrayID == -1: #no ROI Array found
            print " ------------------------------ CREATED ---------------------------------"
            arrayToAdd = vtk.vtkDoubleArray()
            arrayToAdd.SetName(arrayName)
        else:
            print " ----------------------------- MODIFIED ---------------------------------"
            arrayToAdd = pointData.GetArray(arrayID)
            arrayToAdd.Reset()
            arrayToAdd.Resize(0)

        for i in range(0, polyData.GetNumberOfPoints()):
                arrayToAdd.InsertNextValue(0.0)
        for i in range(0, numberofIds):
            arrayToAdd.SetValue(connectedIdList.GetId(i), 1.0)

        lut = vtk.vtkLookupTable()
        tableSize = 2
        lut.SetNumberOfTableValues(tableSize)
        lut.Build()
        lut.SetTableValue(0, 0, 0, 1, 1)
        lut.SetTableValue(1, 1, 0, 0, 1)

        arrayToAdd.SetLookupTable(lut)
        pointData.AddArray(arrayToAdd)
        return True

    def getNeighbor(self, fiducialState ):
        print"----getNeighbor----"
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


        inputModelNode = fiducialState.inputAssociated
        arrayName = fiducialState.arrayName
        polyData = inputModelNode.GetPolyData()
        pointID = fiducialState.indexClosestPoint
        distance = fiducialState.radiusROI
        connectedVerticesList = vtk.vtkIdList()

        connectedVerticesList = GetConnectedVertices(polyData, pointID)
        if distance > 1:
            for dist in range(1, int(distance)):
                for i in range(0, connectedVerticesList.GetNumberOfIds()):
                    connectedList = GetConnectedVertices(polyData, connectedVerticesList.GetId(i))
                    verticesListTemp = add2IdLists(connectedVerticesList, connectedList)
                connectedVerticesList = verticesListTemp

        arrayAddedBool = self.addArray(connectedVerticesList, inputModelNode, arrayName)
        print " arrayAddedBool : ", arrayAddedBool
        if arrayAddedBool:
            self.displayROI(inputModelNode, arrayName)

        return True

    def propagateFiducial(self, fidNode, fiducialToPropagateID,  fiducialToPropagateState, fiducialToAddState, propagateInput ):
        fiducialToPropagateCoord = numpy.zeros(3)
        fidNode.GetNthFiducialPosition(fiducialToPropagateID, fiducialToPropagateCoord)
        fiducialToAddState.fiducialLabel = fiducialToPropagateState.fiducialLabel + "_ROI"

        fiducialToAddState.fiducialScale = 1.0

        fiducialAddedID = fidNode.AddFiducial(fiducialToPropagateCoord[0],
                                              fiducialToPropagateCoord[1],
                                              fiducialToPropagateCoord[2],
                                              fiducialToAddState.fiducialLabel)

        fiducialToAddState.indexClosestPoint = self.getClosestPointIndex(fidNode,
                                                                         propagateInput,
                                                                         fiducialAddedID)

        fiducialToAddState.radiusROI = fiducialToPropagateState.radiusROI
        fiducialToAddState.arrayName = fiducialToPropagateState.arrayName
        fiducialToAddState.mouvementSurfaceStatus = True
