#!/usr/bin/env python
import roslib; roslib.load_manifest('instructor_plugins')
import rospy 
from std_msgs.msg import *
from threading import Thread
# Qt
from PyQt4 import QtGui, QtCore, uic
from PyQt4.QtGui import *
from PyQt4.QtCore import *
# Beetree and Instructor
from service_node import ServiceNode
from instructor_core import NodeGUI
from instructor_core.instructor_qt import NamedField, ColorOptions
import rospkg
from instructor_core.srv import *
import tf; 
import tf_conversions as tf_c
# Driver services for ur5
import costar_robot_msgs
from costar_robot_msgs.srv import *
from smart_waypoint_manager import SmartWaypointManager
from predicator_msgs.msg import *

colors = ColorOptions().colors

GLOBAL_MANAGER = None

# Node Wrappers -----------------------------------------------------------
class NodeActionSmartmoveGUI(NodeGUI):
    def __init__(self):
        super(NodeActionSmartmoveGUI,self).__init__('green')

        rospack = rospkg.RosPack()
        ui_path = rospack.get_path('instructor_plugins') + '/ui/action_smartmove.ui'

        self.title.setText('SMARTMOVE')
        self.title.setStyleSheet('background-color:'+ colors['green'].normal+';color:#ffffff')
        self.setStyleSheet('background-color:'+ colors['green'].normal+' ; color:#ffffff')

        self.waypoint_ui = QWidget()
        uic.loadUi(ui_path, self.waypoint_ui)
        self.layout_.addWidget(self.waypoint_ui)

        self.selected_region = 'none'
        self.selected_reference = 'none'
        self.selected_object = None
        self.selected_smartmove = None

        self.command_waypoint_name = None
        self.command_vel = .75
        self.command_acc = .75
        self.listener_ = tf.TransformListener()

        global GLOBAL_MANAGER
        if GLOBAL_MANAGER is None:
            rospy.loginfo("creating smart waypoint manager")
            GLOBAL_MANAGER = SmartWaypointManager()
        self.manager = GLOBAL_MANAGER

        self.waypoint_ui.reference_list.itemClicked.connect(self.reference_selected_cb)
        self.waypoint_ui.region_list.itemClicked.connect(self.region_selected_cb)
        self.waypoint_ui.object_list.itemClicked.connect(self.object_selected_cb)
        self.waypoint_ui.smartmove_list.itemClicked.connect(self.smartmove_selected_cb)

        self.waypoint_ui.acc_slider.valueChanged.connect(self.acc_changed)
        self.waypoint_ui.vel_slider.valueChanged.connect(self.vel_changed)
        #self.waypoint_ui.refresh_btn.clicked.connect(self.update_relative_waypoints)

        self.manager.load_all()
        self.update_regions()
        self.update_references()
        self.update_objects()
        
    def vel_changed(self,t):
        self.waypoint_ui.vel_field.setText(str(float(t)))
        self.command_vel = float(t)/100*1.5

    def acc_changed(self,t):
        self.waypoint_ui.acc_field.setText(str(float(t)))
        self.command_acc = float(t)/100*1.5

    def reference_selected_cb(self,item):
        self.selected_reference = str(item.text())

    def region_selected_cb(self,item):
        self.selected_region = str(item.text())

    def object_selected_cb(self,item):
        self.selected_object = str(item.text())
        self.update_smartmoves()
        
    def smartmove_selected_cb(self,item):
        self.selected_smartmove = str(item.text())

    def update_regions(self):
        # TODO predicator call to update different region options for the objects (i.e. "left of X")
        # populate regions with result
        # for now loading from librarian
        regions = self.manager.get_available_predicates()

        if regions is None:
          regions = []

        self.waypoint_ui.region_list.clear()
        for m in regions:
            self.waypoint_ui.region_list.addItem(QListWidgetItem(m.strip('/')))
        self.waypoint_ui.region_list.sortItems()
        self.waypoint_ui.region_list.setCurrentRow(0)
        if self.waypoint_ui.region_list.currentItem() is not None and self.selected_region == 'none':
            self.selected_region = str(self.waypoint_ui.region_list.currentItem().text())

    def update_references(self):
        # TODO use a predicator call to populate list of references or look them up on rosparam
        # for now loading from librarian
        references= self.manager.get_reference_frames()

        if references is None:
          references = []

        self.waypoint_ui.reference_list.clear()
        for m in references:
            self.waypoint_ui.reference_list.addItem(QListWidgetItem(m.strip('/')))
        self.waypoint_ui.reference_list.sortItems()
        self.waypoint_ui.reference_list.setCurrentRow(0)
        if self.waypoint_ui.region_list.currentItem() is not None and self.selected_reference == 'none':
            self.selected_reference = str(self.waypoint_ui.region_list.currentItem().text())

    def update_objects(self):
        objects = []
        objects = self.manager.get_available_object_classes()
        self.waypoint_ui.object_list.clear()
        for m in objects:
            self.waypoint_ui.object_list.addItem(QListWidgetItem(m.strip('/')))
        self.waypoint_ui.object_list.sortItems()
        self.waypoint_ui.object_list.setCurrentRow(0)    
        if self.waypoint_ui.object_list.currentItem() is not None and self.selected_object is None:
            self.selected_object = str(self.waypoint_ui.object_list.currentItem().text())

    def update_smartmoves(self):
        smartmoves = []
        smartmoves = self.manager.get_moves_for_class(self.selected_object)
        self.waypoint_ui.smartmove_list.clear()
        for m in smartmoves:
            self.waypoint_ui.smartmove_list.addItem(QListWidgetItem(m.strip('/')))
        self.waypoint_ui.smartmove_list.sortItems()
        self.waypoint_ui.smartmove_list.setCurrentRow(0)  
        if self.waypoint_ui.smartmove_list.currentItem() is not None and self.selected_smartmove is None:
            self.selected_smartmove = str(self.waypoint_ui.smartmove_list.currentItem().text())

    def save_data(self,data):
        data['region'] = {'value':self.selected_region}
        data['object'] = {'value':self.selected_object}
        data['reference'] = {'value':self.selected_reference}
        data['smartmove'] = {'value':self.selected_smartmove}
        data['vel'] = {'value':self.command_vel}
        data['acc'] = {'value':self.command_acc}
        return data

    def load_data(self,data):
        self.manager.load_all()
        if data.has_key('region'):
            if data['region']['value']!=None:
                self.selected_region = (data['region']['value'])
        if data.has_key('object'):
            if data['object']['value']!=None:
                self.selected_object = (data['object']['value'])
        if data.has_key('reference'):
            if data['reference']['value']!=None:
                self.selected_reference = (data['reference']['value'])
        if data.has_key('smartmove'):
            if data['smartmove']['value']!=None:
                self.selected_smartmove = (data['smartmove']['value'])
        if data.has_key('vel'):
            if data['vel']['value']!=None:
                self.command_vel = data['vel']['value']
                self.waypoint_ui.vel_field.setText(str(float(self.command_vel)*100/1.5))
                self.waypoint_ui.vel_slider.setSliderPosition(int(float(self.command_vel)*100/1.5))
        if data.has_key('acc'):
            if data['acc']['value']!=None:
                self.command_acc = data['acc']['value']
                self.waypoint_ui.acc_field.setText(str(float(self.command_acc)*100/1.5))
                self.waypoint_ui.acc_slider.setSliderPosition(int(float(self.command_acc)*100/1.5))
        self.update_regions()
        self.update_references()
        self.update_objects()

    def generate(self):
        if all([self.name.full(), self.selected_object, self.selected_smartmove]):
            # rospy.logwarn('Generating SmartMove with reference='+str(self.selected_reference)+' and smartmove='+str(self.selected_smartmove))
            return NodeActionSmartmove( self.get_name(),
                                        self.get_label(),
                                        self.selected_region,
                                        self.selected_object,
                                        self.selected_smartmove,
                                        self.selected_reference,
                                        self.command_vel,
                                        self.command_acc,
                                        self.manager)

            #"%s %s %s %s"%(self.selected_smartmove,self.selected_objet,self.selected_region,self.selected_reference),
        else:
            rospy.logerr('check that all menu items are properly selected for this node')
            return 'ERROR: check that all menu items are properly selected for this node'

    def refresh_data(self):
        self.manager.load_all()
        self.update_regions()
        self.update_references()
        self.update_objects()

# Nodes -------------------------------------------------------------------
class NodeActionSmartmove(ServiceNode):
    def __init__(self,name,label,selected_region,selected_object,selected_smartmove,selected_reference,vel,acc,smartmove_manager):
        L = 'SMART MOVE to \\n ['+selected_smartmove+'] \\n [' + selected_region + ' ' + selected_reference + ']'
        super(NodeActionSmartmove,self).__init__(name,L,'#26A65B',"SmartMove Service",display_name=selected_smartmove)
        self.selected_region = selected_region
        self.selected_reference = selected_reference
        self.selected_object = selected_object
        self.selected_smartmove = selected_smartmove
        self.command_acc = acc
        self.command_vel = vel
        self.manager = smartmove_manager
        self.listener_ = smartmove_manager.listener

    def make_service_call(self,request,*args):
        self.manager.load_all()

        # Check to see if service exists
        try:
            rospy.wait_for_service('/costar/SmartMove')
        except rospy.ROSException as e:
            rospy.logerr('Could not find SmartMove service')
            self.finished_with_success = False
            return
        # Make servo call to set pose
        try:
            smartmove_proxy = rospy.ServiceProxy('/costar/SmartMove',SmartMove)
            msg = SmartMoveRequest()
            msg.pose = self.manager.lookup_waypoint(self.selected_object,self.selected_smartmove)
            if msg.pose is None:
                rospy.logerr('Invalid Smarresulttmove Waypoint')
                self.finished_with_success = False
                return 
            msg.obj_class = self.selected_object
            msg.name = self.selected_smartmove
            predicate = PredicateStatement()
            predicate.predicate = self.selected_region 
            predicate.params = ['*',self.selected_reference,'world']
            msg.predicates = [predicate]
            msg.vel = self.command_vel
            msg.accel = self.command_acc
            # Send SmartMove Command
            rospy.loginfo('SmartMove Started')
            result = smartmove_proxy(msg)
            if 'FAILURE' in str(result.ack):
                rospy.logwarn('Servo failed with reply: '+ str(result.ack))
                self.finished_with_success = False
                return
            else:
                rospy.loginfo('Single Servo Move Finished')
                rospy.logwarn('Robot driver reported: '+str(result.ack))
                self.finished_with_success = True
                return

        except (tf.LookupException, tf.ConnectivityException, tf.ExtrapolationException), e:
            rospy.logerr('There was a problem with the tf lookup:')
            rospy.logerr(e)
            self.finished_with_success = False
            return
        except rospy.ServiceException, e:
            rospy.logwarn('Service failed!')
            rospy.logerr(e)
            self.finished_with_success = False
            return
