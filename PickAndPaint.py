import vtk, qt, ctk, slicer
import numpy
import time
from slicer.ScriptedLoadableModule import *


class PickAndPaint(ScriptedLoadableModule):
    def __init__(self, parent):
      ScriptedLoadableModule.__init__(self, parent)
      parent.title = "Pick 'n Paint "
      parent.categories = ["Shape Analysis"]
      self.parent.dependencies = []
      self.parent.contributors = ["Lucie Macron (University Of Michigan)"]
      self.parent.helpText = """
          Pick 'n Paint tool allows users to select ROIs on a reference model and to propagate it over different time point models.
          """
      self.parent.acknowledgementText = """
          This work was supported by the National Institues of Dental and Craniofacial Research and Biomedical Imaging and Bioengineering of the National Institutes of Health under Award Number R01DE024450.
          """

class PickAndPaintWidget(ScriptedLoadableModuleWidget):
    class fiducialState(object):
        def __init__(self):
            self.fiducialLabel = None
            self.fiducialScale = 2.0
            self.radiusROI = 0.0
            self.indexClosestPoint = -1
            self.arrayName = None
            self.mouvementSurfaceStatus = True
            self.propagatedBool = False

    class inputState (object):
        def __init__(self):
            self.inputModelNode = None
            self.fidNodeID = None
            self.MarkupAddedEventTag = None
            self.PointModifiedEventTag = None
            self.dictionaryLandmark = dict()  # Key = ID of markups
            self.dictionaryLandmark.clear()

            # ------------------------- PROPAGATION ------------------------
            self.dictionaryPropInput = dict()  # Key = ID of Propagated Model Node
            self.dictionaryPropInput.clear()
            self.propagationType = 0  #  Type of propagation
                                      #  0: No type specified
                                      #  1: Correspondent Shapes
                                      #  2: Non Correspondent Shapes

    def setup(self):
        print " ----- SetUp ------"
        ScriptedLoadableModuleWidget.setup(self)
        # ------------------------------------------------------------------------------------
        #                                   Global Variables
        # ------------------------------------------------------------------------------------
        self.logic = PickAndPaintLogic()

        self.dictionaryInput = dict()
        self.dictionaryInput.clear()

        self.propInputID = -1

        # ------ REVIEW PROPAGATED MESHES --------------
        self.propMarkupsNode = slicer.vtkMRMLMarkupsFiducialNode()
        self.propMarkupsNode.SetName('PropagationMarkupsNode')
        self.PropPointModifiedEventTag = None
        self.propLandmarkIndex = -1
        self.refLandmarkID = None

        #-------------------------------------------------------------------------------------
        # Interaction with 3D Scene
        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
        self.interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")

        #-------------------------------------------------------------------------------------
        # ------------------------------------------------------------------------------------
        #                                    Input Selection
        # ------------------------------------------------------------------------------------
        inputLabel = qt.QLabel("Model of Reference: ")

        self.inputModelSelector = slicer.qMRMLNodeComboBox()
        self.inputModelSelector.objectName = 'inputFiducialsNodeSelector'
        self.inputModelSelector.nodeTypes = ['vtkMRMLModelNode']
        self.inputModelSelector.selectNodeUponCreation = False
        self.inputModelSelector.addEnabled = False
        self.inputModelSelector.removeEnabled = False
        self.inputModelSelector.noneEnabled = True
        self.inputModelSelector.showHidden = False
        self.inputModelSelector.showChildNodeTypes = False
        self.inputModelSelector.setMRMLScene(slicer.mrmlScene)

        inputModelSelectorFrame = qt.QFrame(self.parent)
        inputModelSelectorFrame.setLayout(qt.QHBoxLayout())
        inputModelSelectorFrame.layout().addWidget(inputLabel)
        inputModelSelectorFrame.layout().addWidget(self.inputModelSelector)

        #  ------------------------------------------------------------------------------------
        #                                   BUTTONS
        #  ------------------------------------------------------------------------------------
        #  ------------------------------- Add Fiducials Group --------------------------------
        # Fiducials Scale
        self.fiducialsScaleWidget = ctk.ctkSliderWidget()
        self.fiducialsScaleWidget.singleStep = 0.1
        self.fiducialsScaleWidget.minimum = 0.1
        self.fiducialsScaleWidget.maximum = 20.0
        self.fiducialsScaleWidget.value = 2.0
        fiducialsScaleLayout = qt.QFormLayout()
        fiducialsScaleLayout.addRow("Scale: ", self.fiducialsScaleWidget)

        # Add Fiducials Button
        self.addFiducialsButton = qt.QPushButton(" Add ")
        self.addFiducialsButton.enabled = True

        # Movements on the surface
        self.surfaceDeplacementCheckBox = qt.QCheckBox("On Surface")
        self.surfaceDeplacementCheckBox.setChecked(True)

        # Layouts
        scaleAndAddFiducialLayout = qt.QHBoxLayout()
        scaleAndAddFiducialLayout.addWidget(self.addFiducialsButton)
        scaleAndAddFiducialLayout.addLayout(fiducialsScaleLayout)
        scaleAndAddFiducialLayout.addWidget(self.surfaceDeplacementCheckBox)

        # Add Fiducials GroupBox
        addFiducialBox = qt.QGroupBox()
        addFiducialBox.title = " Landmarks "
        addFiducialBox.setLayout(scaleAndAddFiducialLayout)

        #  ----------------------------------- ROI Group ------------------------------------
        # ROI GroupBox
        self.roiGroupBox = qt.QGroupBox()
        self.roiGroupBox.title = "Region of interest"

        self.fiducialComboBoxROI = qt.QComboBox()

        self.radiusDefinitionWidget = ctk.ctkSliderWidget()
        self.radiusDefinitionWidget.singleStep = 1.0
        self.radiusDefinitionWidget.minimum = 0.0
        self.radiusDefinitionWidget.maximum = 20.0
        self.radiusDefinitionWidget.value = 0.0
        self.radiusDefinitionWidget.tracking = False

        roiBoxLayout = qt.QFormLayout()
        roiBoxLayout.addRow("Select a Fiducial:", self.fiducialComboBoxROI)
        roiBoxLayout.addRow("Value of radius", self.radiusDefinitionWidget)
        self.roiGroupBox.setLayout(roiBoxLayout)

        self.ROICollapsibleButton = ctk.ctkCollapsibleButton()
        self.ROICollapsibleButton.setText("Selection Region of Interest: ")
        self.parent.layout().addWidget(self.ROICollapsibleButton)

        ROICollapsibleButtonLayout = qt.QVBoxLayout()
        ROICollapsibleButtonLayout.addWidget(inputModelSelectorFrame)
        ROICollapsibleButtonLayout.addWidget(addFiducialBox)
        ROICollapsibleButtonLayout.addWidget(self.roiGroupBox)
        self.ROICollapsibleButton.setLayout(ROICollapsibleButtonLayout)

        self.ROICollapsibleButton.checked = True
        self.ROICollapsibleButton.enabled = True

        #  ----------------------------- Propagate Button ----------------------------------
        self.propagationCollapsibleButton = ctk.ctkCollapsibleButton()
        self.propagationCollapsibleButton.setText(" Propagation: ")
        self.parent.layout().addWidget(self.propagationCollapsibleButton)

        self.shapesLayout = qt.QHBoxLayout()
        self.correspondentShapes = qt.QRadioButton('Correspondent Meshes')
        self.correspondentShapes.setChecked(True)
        self.nonCorrespondentShapes = qt.QRadioButton('Non Correspondent Meshes')
        self.nonCorrespondentShapes.setChecked(False)
        self.shapesLayout.addWidget(self.correspondentShapes)
        self.shapesLayout.addWidget(self.nonCorrespondentShapes)

        self.propagationInputComboBox = slicer.qMRMLCheckableNodeComboBox()
        self.propagationInputComboBox.nodeTypes = ['vtkMRMLModelNode']
        self.propagationInputComboBox.setMRMLScene(slicer.mrmlScene)

        self.propagateButton = qt.QPushButton("Propagate")
        self.propagateButton.enabled = True

        propagationBoxLayout = qt.QVBoxLayout()
        propagationBoxLayout.addLayout(self.shapesLayout)
        propagationBoxLayout.addWidget(self.propagationInputComboBox)
        propagationBoxLayout.addWidget(self.propagateButton)

        self.propagationCollapsibleButton.setLayout(propagationBoxLayout)
        self.propagationCollapsibleButton.checked = False
        self.propagationCollapsibleButton.enabled = True

        self.layout.addStretch(1)
        # ------------------------------------------------------------------------------------
        #                                   CONNECTIONS
        # ------------------------------------------------------------------------------------
        self.inputModelSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.onCurrentNodeChanged)
        self.addFiducialsButton.connect('clicked()', self.onAddButton)
        self.fiducialsScaleWidget.connect('valueChanged(double)', self.onFiducialsScaleChanged)
        self.surfaceDeplacementCheckBox.connect('stateChanged(int)', self.onSurfaceDeplacementStateChanged)
        self.fiducialComboBoxROI.connect('currentIndexChanged(QString)', self.onFiducialComboBoxROIChanged)
        self.radiusDefinitionWidget.connect('valueChanged(double)', self.onRadiusValueChanged)
        self.radiusDefinitionWidget.connect('valueIsChanging(double)', self.onRadiusValueIsChanging)

        self.propagationInputComboBox.connect('checkedNodesChanged()', self.onPropagationInputComboBoxCheckedNodesChanged)
        self.propagateButton.connect('clicked()', self.onPropagateButton)


        def onCloseScene(obj, event):
            # initialize Parameters
            globals()["PickAndPaint"] = slicer.util.reloadScriptedModule("PickAndPaint")
        slicer.mrmlScene.AddObserver(slicer.mrmlScene.EndCloseEvent, onCloseScene)


    def UpdateInterface(self):
        print " OnUpdateInterface "
        if self.inputModelSelector.currentNode():
            activeInputID = self.inputModelSelector.currentNode().GetID()
            selectedFidReflID = self.logic.findIDFromLabel(self.dictionaryInput[activeInputID].dictionaryLandmark,
                                                           self.fiducialComboBoxROI.currentText)
            if activeInputID != -1:
                # Reset all Values
                if self.dictionaryInput[activeInputID].dictionaryLandmark and selectedFidReflID:
                    activeDictLandmarkValue = self.dictionaryInput[activeInputID].dictionaryLandmark[selectedFidReflID]
                    self.fiducialsScaleWidget.value = activeDictLandmarkValue.fiducialScale
                    self.radiusDefinitionWidget.value = activeDictLandmarkValue.radiusROI
                    if activeDictLandmarkValue.mouvementSurfaceStatus:
                        self.surfaceDeplacementCheckBox.setChecked(True)
                    else:
                        self.surfaceDeplacementCheckBox.setChecked(False)
                else:
                    self.radiusDefinitionWidget.value = 0.0
                    self.fiducialsScaleWidget.value = 2.0

                self.logic.UpdateThreeDView(self.inputModelSelector.currentNode(),
                                            self.dictionaryInput,
                                            self.fiducialComboBoxROI.currentText,
                                            "UpdateInterface")

    def onCurrentNodeChanged(self):
        print " ------------------------------------ onCurrentNodeChanged ------------------------------------"
        if self.inputModelSelector.currentNode():
            activeInputID = self.inputModelSelector.currentNode().GetID()
            if activeInputID:
                if not self.dictionaryInput.has_key(activeInputID):
                    self.dictionaryInput[activeInputID] = self.inputState()
                    # self.dictionaryInput[activeInputID].inputModelNode = activeInput
                    fidNode  = slicer.vtkMRMLMarkupsFiducialNode()
                    slicer.mrmlScene.AddNode(fidNode)
                    self.dictionaryInput[activeInputID].fidNodeID = fidNode.GetID()

                    # Observers Fiducials Node:
                    self.dictionaryInput[activeInputID].MarkupAddedEventTag = \
                        fidNode.AddObserver(fidNode.MarkupAddedEvent, self.onMarkupAddedEvent)

                    self.dictionaryInput[activeInputID].PointModifiedEventTag = \
                        fidNode.AddObserver(fidNode.PointModifiedEvent, self.onPointModifiedEvent)
                else:
                    print "Key already exists"
                    slicer.modules.markups.logic().SetActiveListID(slicer.mrmlScene.GetNodeByID(self.dictionaryInput[activeInputID].fidNodeID))


                # Update Fiducial ComboBox and PropFidComboBox
                self.fiducialComboBoxROI.clear()
                fidNode = slicer.app.mrmlScene().GetNodeByID(self.dictionaryInput[activeInputID].fidNodeID)
                if fidNode:
                    numOfFid = fidNode.GetNumberOfMarkups()
                    if numOfFid > 0:
                        if self.fiducialComboBoxROI.count == 0:
                            for i in range(0, numOfFid):
                                landmarkLabel = fidNode.GetNthMarkupLabel(i)
                                self.fiducialComboBoxROI.addItem(landmarkLabel)

                for node in self.propagationInputComboBox.checkedNodes():
                    print node.GetName()
                    self.propagationInputComboBox.setCheckState(node, 0)

                self.logic.UpdateThreeDView(self.inputModelSelector.currentNode(),
                                            self.dictionaryInput,
                                            self.fiducialComboBoxROI.currentText,
                                            'onCurrentNodeChanged')
            else:
                print ' Input chosen: None! '

    def onAddButton(self):
        self.interactionNode.SetCurrentInteractionMode(1)

    def onFiducialsScaleChanged(self):
        print " ------------------------------------ onFiducialsScaleChanged ------------------------------------ "
        if self.inputModelSelector.currentNode():
            activeInput = self.inputModelSelector.currentNode()
            fidNode = slicer.app.mrmlScene().GetNodeByID(self.dictionaryInput[activeInput.GetID()].fidNodeID)
            if activeInput:
                for value in self.dictionaryInput[activeInput.GetID()].dictionaryLandmark.itervalues():
                    value.fiducialScale = self.fiducialsScaleWidget.value
                    print value.fiducialScale
                if fidNode:
                    displayFiducialNode = fidNode.GetMarkupsDisplayNode()
                    disabledModify = displayFiducialNode.StartModify()
                    displayFiducialNode.SetGlyphScale(self.fiducialsScaleWidget.value)
                    displayFiducialNode.SetTextScale(self.fiducialsScaleWidget.value)
                    displayFiducialNode.EndModify(disabledModify)
                else:
                    print "Error with fiducialNode"

    def onSurfaceDeplacementStateChanged(self):
        print " ------------------------------------ onSurfaceDeplacementStateChanged ------------------------------------"
        if self.inputModelSelector.currentNode():
            activeInput = self.inputModelSelector.currentNode()
            fidNode = slicer.app.mrmlScene().GetNodeByID(self.dictionaryInput[activeInput.GetID()].fidNodeID)

            selectedFidReflID = self.logic.findIDFromLabel(self.dictionaryInput[activeInput.GetID()].dictionaryLandmark,
                                                           self.fiducialComboBoxROI.currentText)
            if selectedFidReflID:
                if self.surfaceDeplacementCheckBox.isChecked():
                    self.dictionaryInput[activeInput.GetID()].dictionaryLandmark[selectedFidReflID].mouvementSurfaceStatus = True
                    for key, value in self.dictionaryInput[activeInput.GetID()].dictionaryLandmark.iteritems():
                        markupsIndex = fidNode.GetMarkupIndexByID(key)
                        if value.mouvementSurfaceStatus:
                           value.indexClosestPoint = self.logic.getClosestPointIndex(fidNode,
                                                                                     slicer.util.getNode(activeInput.GetID()),
                                                                                     markupsIndex)
                           self.logic.replaceLandmark(slicer.util.getNode(activeInput.GetID()),
                                                      fidNode,
                                                      markupsIndex,
                                                      value.indexClosestPoint)
                else:
                    self.dictionaryInput[activeInput.GetID()].dictionaryLandmark[selectedFidReflID].mouvementSurfaceStatus = False

    def onFiducialComboBoxROIChanged(self):
        print "-------- ComboBox changement --------"
        self.UpdateInterface()

    def onRadiusValueIsChanging(self):
        print " ------------------------------------ onRadiusValueIsChanging ------------------------------------"

    def onRadiusValueChanged(self):
        print " ------------------------------------ onRadiusValueChanged ---------------------------------------"
        if self.inputModelSelector.currentNode():
            activeInput = self.inputModelSelector.currentNode()
            selectedFidReflID = self.logic.findIDFromLabel(self.dictionaryInput[activeInput.GetID()].dictionaryLandmark,
                                                           self.fiducialComboBoxROI.currentText)
            if selectedFidReflID and self.radiusDefinitionWidget.value != 0:
                activeLandmarkState = self.dictionaryInput[activeInput.GetID()].dictionaryLandmark[selectedFidReflID]
                activeLandmarkState.radiusROI = self.radiusDefinitionWidget.value
            #     if self.activeDictionaryInputKey:
                if not activeLandmarkState.mouvementSurfaceStatus:
                    self.surfaceDeplacementCheckBox.setChecked(True)
                    activeLandmarkState.mouvementSurfaceStatus = True

                self.radiusDefinitionWidget.setEnabled(False)
                listID = self.logic.defineNeighbor(activeInput,
                                                   activeLandmarkState.indexClosestPoint,
                                                   activeLandmarkState.radiusROI)
                self.logic.addArrayFromIdList(listID, activeInput, activeLandmarkState.arrayName)
                self.logic.displayROI(activeInput, activeLandmarkState.arrayName)
                self.radiusDefinitionWidget.setEnabled(True)
            self.radiusDefinitionWidget.tracking = False

    def onPropagationInputComboBoxCheckedNodesChanged(self):
        if self.inputModelSelector.currentNode():
            activeInput = self.inputModelSelector.currentNode()
            if activeInput:
                self.dictionaryInput[activeInput.GetID()].dictionaryPropInput.clear()
                list = self.propagationInputComboBox.checkedNodes()
            for model in list:
                if model.GetID() != activeInput.GetID():
                    self.dictionaryInput[activeInput.GetID()].dictionaryPropInput[model.GetID()] = dict()
            print self.dictionaryInput[activeInput.GetID()].dictionaryPropInput

    def onPropagateButton(self):
        print " ------------------------------------ onPropagateButton -------------------------------------- "
        if self.inputModelSelector.currentNode():
            activeInput = self.inputModelSelector.currentNode()
            if self.correspondentShapes.isChecked():
                # print "CorrespondentShapes"
                self.dictionaryInput[activeInput.GetID()].propagationType = 1
                for value in self.dictionaryInput[activeInput.GetID()].dictionaryLandmark.itervalues():
                    arrayName = value.arrayName
                    value.propagatedBool = True
                    for IDModel in self.dictionaryInput[activeInput.GetID()].dictionaryPropInput.iterkeys():
                        model = slicer.mrmlScene.GetNodeByID(IDModel)
                        self.logic.propagateCorrespondent(activeInput, model, arrayName)
            else:
                # print "nonCorrespondentShapes"
                self.dictionaryInput[activeInput.GetID()].propagationType = 2
                for fiducialID, fiducialState in self.dictionaryInput[activeInput.GetID()].dictionaryLandmark.iteritems():
                    fiducialState.propagatedBool = True
                    for IDModel, dict in self.dictionaryInput[activeInput.GetID()].dictionaryPropInput.iteritems():
                        model = slicer.mrmlScene.GetNodeByID(IDModel)
                        self.logic.propagateNonCorrespondent(self.dictionaryInput[activeInput.GetID()].fidNodeID,
                                                             fiducialID,
                                                             fiducialState,
                                                             model)
            self.UpdateInterface()


    def onMarkupAddedEvent (self, obj, event):
        if self.inputModelSelector.currentNode():
            print" ------------------------------------ onMarkupAddedEvent --------------------------------------"
            activeInput = self.inputModelSelector.currentNode()
            # print " Number of Fiducial ", obj.GetNumberOfMarkups()
            numOfMarkups = obj.GetNumberOfMarkups()
            markupID = obj.GetNthMarkupID(numOfMarkups-1)

            self.dictionaryInput[activeInput.GetID()].dictionaryLandmark[markupID] = self.fiducialState()

            fiducialLabel = '  ' + str(numOfMarkups)
            self.dictionaryInput[activeInput.GetID()].dictionaryLandmark[markupID].fiducialLabel = fiducialLabel

            obj.SetNthFiducialLabel(numOfMarkups-1, fiducialLabel)

            arrayName = activeInput.GetName()+'_'+str(numOfMarkups)+"_ROI"
            self.dictionaryInput[activeInput.GetID()].dictionaryLandmark[markupID].arrayName = arrayName
            #
            self.fiducialComboBoxROI.addItem(fiducialLabel)
            self.fiducialComboBoxROI.setCurrentIndex(self.fiducialComboBoxROI.count-1)

            self.UpdateInterface()

    def onPointModifiedEvent ( self, obj, event):
        print " ------------------------------------ onPointModifiedEvent -------------------------------------- "
        if self.inputModelSelector.currentNode():
            activeInput = self.inputModelSelector.currentNode()
            fidNode = slicer.app.mrmlScene().GetNodeByID(self.dictionaryInput[activeInput.GetID()].fidNodeID)
            # remove observer to make sure, the callback function won't be disturbed
            fidNode.RemoveObserver(self.dictionaryInput[activeInput.GetID()].PointModifiedEventTag)
            selectedFiducialID = self.logic.findIDFromLabel(self.dictionaryInput[activeInput.GetID()].dictionaryLandmark,
                                                            self.fiducialComboBoxROI.currentText)
            activeLandmarkState = self.dictionaryInput[activeInput.GetID()].dictionaryLandmark[selectedFiducialID]
            markupsIndex = fidNode.GetMarkupIndexByID(selectedFiducialID)
            if activeLandmarkState.mouvementSurfaceStatus:
                activeLandmarkState.indexClosestPoint = self.logic.getClosestPointIndex(fidNode,
                                                                                        slicer.util.getNode(activeInput.GetID()),
                                                                                        markupsIndex)
                self.logic.replaceLandmark(slicer.util.getNode(activeInput.GetID()),
                                           fidNode,
                                           markupsIndex,
                                           activeLandmarkState.indexClosestPoint)

            # Moving the region if we move the fiducial
            if activeLandmarkState.radiusROI > 0 and activeLandmarkState.radiusROI != 0:
                listID = self.logic.defineNeighbor(activeInput,
                                                   activeLandmarkState.indexClosestPoint,
                                                   activeLandmarkState.radiusROI)
                self.logic.addArrayFromIdList(listID, activeInput, activeLandmarkState.arrayName)
                self.logic.displayROI(activeInput, activeLandmarkState.arrayName)

                # Moving the region on propagated models if the region has been propagated before
                if self.dictionaryInput[activeInput.GetID()].dictionaryPropInput and activeLandmarkState.propagatedBool:
                    if self.correspondentShapes.isChecked():
                        print " self.correspondentShapes.isChecked "
                        for nodeID in self.dictionaryInput[activeInput.GetID()].dictionaryPropInput.iterkeys():
                            print nodeID
                            node = slicer.mrmlScene.GetNodeByID(nodeID)
                            self.logic.propagateCorrespondent(activeInput, node, activeLandmarkState.arrayName)
                    else:
                        print " Not Checked "
                        for nodeID in self.dictionaryInput[activeInput.GetID()].dictionaryPropInput.iterkeys():
                            print nodeID
                            node = slicer.mrmlScene.GetNodeByID(nodeID)
                            self.logic.propagateNonCorrespondent(self.dictionaryInput[activeInput.GetID()].fidNodeID,
                                                                 selectedFiducialID,
                                                                 activeLandmarkState,
                                                                 node)
            time.sleep(0.08)
            self.dictionaryInput[activeInput.GetID()].PointModifiedEventTag = \
                fidNode.AddObserver(fidNode.PointModifiedEvent, self.onPointModifiedEvent)

class PickAndPaintLogic(ScriptedLoadableModuleLogic):
    def __init__(self):
        pass
    def findIDFromLabel(self, activeInputLandmarkDict, fiducialLabel):
        print " findIDFromLabel "
        fiducialID = None
        for ID, value in activeInputLandmarkDict.iteritems():
            if activeInputLandmarkDict[ID].fiducialLabel == fiducialLabel:
                fiducialID = ID
                break
        return fiducialID

    def UpdateThreeDView(self, activeInput, dictionaryInput, landmarkLabel = None, functionCaller = None):
        print " UpdateThreeDView() "
        activeInputID = activeInput.GetID()
        if functionCaller == 'onCurrentNodeChanged':
            # Fiducial Visibility
            for keyInput, valueInput in dictionaryInput.iteritems():
                fidNode = slicer.app.mrmlScene().GetNodeByID(valueInput.fidNodeID)
                if keyInput != activeInputID:
                    if valueInput.dictionaryLandmark:
                        for landID in valueInput.dictionaryLandmark.iterkeys():
                            print "ID=", landID
                            landmarkIndex = fidNode.GetMarkupIndexByID(landID)
                            print "Index= ", landmarkIndex
                            fidNode.SetNthFiducialVisibility(landmarkIndex, False)
                else:
                    if valueInput.dictionaryLandmark:
                        for landID in valueInput.dictionaryLandmark.iterkeys():
                            landmarkIndex = fidNode.GetMarkupIndexByID(landID)
                            fidNode.SetNthFiducialVisibility(landmarkIndex, True)

        if functionCaller == 'UpdateInterface' and landmarkLabel:
            selectedFidReflID = self.findIDFromLabel(dictionaryInput[activeInput.GetID()].dictionaryLandmark,
                                                     landmarkLabel)
            fidNode = slicer.app.mrmlScene().GetNodeByID(dictionaryInput[activeInputID].fidNodeID)
            for key in dictionaryInput[activeInputID].dictionaryLandmark.iterkeys():
                markupsIndex = fidNode.GetMarkupIndexByID(key)
                if key != selectedFidReflID:
                    fidNode.SetNthMarkupLocked(markupsIndex, True)
                else:
                    fidNode.SetNthMarkupLocked(markupsIndex, False)

            displayNode = activeInput.GetModelDisplayNode()
            displayNode.SetScalarVisibility(False)
            if dictionaryInput[activeInput.GetID()].dictionaryPropInput:
                for nodeID in dictionaryInput[activeInput.GetID()].dictionaryPropInput:
                    node = slicer.mrmlScene.GetNodeByID(nodeID)
                    node.GetDisplayNode().SetScalarVisibility(False)
            if selectedFidReflID:
                if dictionaryInput[activeInput.GetID()].dictionaryLandmark[selectedFidReflID].radiusROI > 0:
                    displayNode.SetActiveScalarName(dictionaryInput[activeInput.GetID()].dictionaryLandmark[selectedFidReflID].arrayName)
                    displayNode.SetScalarVisibility(True)
                    for nodeID in dictionaryInput[activeInput.GetID()].dictionaryPropInput:
                        node = slicer.mrmlScene.GetNodeByID(nodeID)
                        arrayID = self.findArray(node.GetPolyData().GetPointData(),
                                                 dictionaryInput[activeInput.GetID()].dictionaryLandmark[selectedFidReflID].arrayName)
                        if arrayID != -1:
                            node.GetDisplayNode().SetActiveScalarName(dictionaryInput[activeInput.GetID()].dictionaryLandmark[selectedFidReflID].arrayName)
                            node.GetDisplayNode().SetScalarVisibility(True)

    def replaceLandmark(self, inputModel, fidNode, fiducialID, indexClosestPoint):
        print " --- replaceLandmark --- "
        polyData = inputModel.GetPolyData()
        fiducialCoord = numpy.zeros(3)
        polyData.GetPoints().GetPoint(indexClosestPoint, fiducialCoord)
        fidNode.SetNthFiducialPosition(fiducialID,
                                       fiducialCoord[0],
                                       fiducialCoord[1],
                                       fiducialCoord[2])

    def getClosestPointIndex(self, fidNode,  input, fiducialID):
        print " --- getClosestPointIndex --- "
        fiducialCoord = numpy.zeros(3)
        fidNode.GetNthFiducialPosition(fiducialID, fiducialCoord)
        polyData = input.GetPolyData()

        pointLocator = vtk.vtkPointLocator()
        pointLocator.SetDataSet(polyData)
        pointLocator.AutomaticOn()
        pointLocator.BuildLocator()
        indexClosestPoint = pointLocator.FindClosestPoint(fiducialCoord)

        return indexClosestPoint


    def displayROI(self, inputModelNode, scalarName):
        print " --- displayROI --- "
        polyData = inputModelNode.GetPolyData()
        polyData.Modified()
        displayNode = inputModelNode.GetModelDisplayNode()
        disabledModify = displayNode.StartModify()

        displayNode.SetActiveScalarName(scalarName)
        displayNode.SetScalarVisibility(True)

        displayNode.EndModify(disabledModify)


    def findArray(self, pointData, arrayName):
        print " --- findArray --- "
        arrayID = -1
        if pointData.HasArray(arrayName) == 1:
            for i in range(0, pointData.GetNumberOfArrays()):
                if pointData.GetArrayName(i) == arrayName:
                    arrayID = i
                    break
        return arrayID


    def addArrayFromIdList(self, connectedIdList, inputModelNode, arrayName):
        print " --- addArrayFromIdList --- "
        polyData = inputModelNode.GetPolyData()
        pointData = polyData.GetPointData()
        numberofIds = connectedIdList.GetNumberOfIds()
        hasArrayInt = pointData.HasArray(arrayName)

        if hasArrayInt == 1:  #  ROI Array found
            print "  MODIFIED "
            pointData.RemoveArray(arrayName)

        print "  CREATED  "
        arrayToAdd = vtk.vtkDoubleArray()
        arrayToAdd.SetName(arrayName)
        for i in range(0, polyData.GetNumberOfPoints()):
                arrayToAdd.InsertNextValue(0.0)
        for i in range(0, numberofIds):
            arrayToAdd.SetValue(connectedIdList.GetId(i), 1.0)

        lut = vtk.vtkLookupTable()
        tableSize = 2
        lut.SetNumberOfTableValues(tableSize)
        lut.Build()
        lut.SetTableValue(0, 0.23, 0.11, 0.8, 1)
        # lut.SetTableValue(1, 0.8, 0.4, 0.9, 1)
        lut.SetTableValue(1, 0.8, 0.3, 0.7, 1)

        arrayToAdd.SetLookupTable(lut)
        pointData.AddArray(arrayToAdd)
        polyData.Modified()
        return True


    def GetConnectedVertices(self, polyData, pointID):
        # print " --- GetConnectedVertices --- "
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


    def defineNeighbor(self, inputModelNode, indexClosestPoint , distance):
        print" --- defineNeighbor --- "
        def add2IdLists(list1, list2):
            for i in range(0, list2.GetNumberOfIds()):
                list1.InsertUniqueId(list2.GetId(i))
            return list1
        polyData = inputModelNode.GetPolyData()
        connectedVerticesList = self.GetConnectedVertices(polyData, indexClosestPoint)
        if distance > 1:
            for dist in range(1, int(distance)):
                for i in range(0, connectedVerticesList.GetNumberOfIds()):
                    connectedList = self.GetConnectedVertices(polyData, connectedVerticesList.GetId(i))
                    verticesListTemp = add2IdLists(connectedVerticesList, connectedList)
                connectedVerticesList = verticesListTemp
        return connectedVerticesList


    def propagateCorrespondent(self, referenceInputModel, propagatedInputModel, arrayName):
        print " ---- propagateCorrespondent ---- "
        referencePointData = referenceInputModel.GetPolyData().GetPointData()
        propagatedPointData = propagatedInputModel.GetPolyData().GetPointData()
        arrayIDReference = self.findArray(referencePointData, arrayName)
        arrayToPropagate = referencePointData.GetArray(arrayIDReference)
        propagatedPointData.AddArray(arrayToPropagate)
        self.displayROI(propagatedInputModel, arrayName)
        arrayIDPropagated = self.findArray(propagatedPointData, arrayName)
        if arrayIDReference != -1:
            arrayToPropagate = referencePointData.GetArray(arrayIDReference)
            if arrayIDPropagated != -1:
                propagatedPointData.RemoveArray(arrayIDPropagated)
            propagatedPointData.AddArray(arrayToPropagate)
            self.displayROI(propagatedInputModel, arrayName)
        else:
            print " NO ROI ARRAY FOUND. PLEASE DEFINE ONE BEFORE."
            pass

    def propagateNonCorrespondent(self, fidNodeID, fiducialID, fiducialState,  propagatedInput):
        fidNode = slicer.app.mrmlScene().GetNodeByID(fidNodeID)
        index = fidNode.GetMarkupIndexByID(fiducialID)
        indexClosestPoint = self.getClosestPointIndex(fidNode, propagatedInput, index)
        listID = self.defineNeighbor(propagatedInput, indexClosestPoint, fiducialState.radiusROI)
        self.addArrayFromIdList(listID, propagatedInput, fiducialState.arrayName)
        self.displayROI(propagatedInput, fiducialState.arrayName)

class PickAndPaintTest(ScriptedLoadableModuleTest):
    def setUp(self):
        slicer.mrmlScene.Clear(0)

    def runTest(self):
        print "TESTESTESTEST"
        self.defineSphere()

    def defineSphere(self):
        renderer = vtk.vtkRenderer()
        rendererWindow = vtk.vtkRenderWindow()
        rendererWindow.AddRenderer(renderer)
        rendererWindowInteractor = vtk.vtkRenderWindowInteractor()
        rendererWindowInteractor.SetRenderWindow(rendererWindow)

        sphereSource = vtk.vtkSphereSource()
        sphereSource.SetCenter(0,0,0)
        sphereSource.SetRadius(5.0)

        mapper = vtk.vtkPolyDataMapper()
        if vtk.VTK_MAJOR_VERSION <= 5:
            mapper.SetInput(sphereSource.GetOutput())
        else:
            mapper.SetInputConnection(sphereSource.GetOutputPort())
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        renderer.AddActor(actor)
        rendererWindowInteractor.Initialize()
        rendererWindow.Render()
        rendererWindowInteractor.Start()

