
import rospy
import urx
import numpy as np
import tf_conversions.posemath as pm
from costar_robot import CostarArm
from sensor_msgs.msg import JointState
from std_msgs.msg import Header

from trajectory_msgs.msg import JointTrajectoryPoint
from trajectory_msgs.msg import JointTrajectory

# for creating client for ur_modern_driver
import actionlib

# for actions
from control_msgs.msg import FollowJointTrajectoryAction
from control_msgs.msg import FollowJointTrajectoryActionGoal
from control_msgs.msg import FollowJointTrajectoryGoal

mode = {'TEACH':'TeachArm', 'SERVO':'MoveArmJointServo', 'SHUTDOWN':'ShutdownArm', 'IDLE':'PauseArm'}

class CostarUR5Driver(CostarArm):

    def __init__(self,ip_address,simulation=False,
            world="/world",
            listener=None,
            traj_step_t=0.1,
            max_acc=1,
            max_vel=1,
            max_goal_diff = 0.02,
            goal_rotation_weight = 0.01,
            max_q_diff = 1e-6):

        if not simulation:
            self.ur = urx.Robot(ip_address)
        self.simulation = simulation

        base_link = "base_link"
        end_link = "ee_link"
        planning_group = "manipulator"
        super(CostarUR5Driver, self).__init__(base_link,end_link,planning_group,
            steps_per_meter=10,
            base_steps=10,
            dof=6,
            closed_form_IK_solver=True)

        self.client = client = actionlib.SimpleActionClient('follow_joint_trajectory',FollowJointTrajectoryAction)

    '''
    Send a whole joint trajectory message to a robot...
    that is listening to individual joint states.
    '''
    def send_trajectory(self,traj,acceleration=0.5,velocity=0.5,cartesian=False,linear=False):

        rate = rospy.Rate(30)
        t = rospy.Time(0)

        stamp = rospy.Time.now().to_sec()
        self.cur_stamp = stamp

        if self.simulation:
            if not linear:
                for pt in traj.points[:-1]:
                    if not cartesian:
                        self.send_q(pt.positions,acceleration,velocity)
                    else:
                        self.send_cart(pt.positions,acceleration,velocity) ##
                    self.set_goal(pt.positions)

                    print " -- %s"%(str(pt.positions))
                    start_t = rospy.Time.now()

                    if self.cur_stamp > stamp:
                        return 'FAILURE - preempted'

                    rospy.sleep(rospy.Duration(pt.time_from_start.to_sec() - t.to_sec()))
                    t = pt.time_from_start

            print " -- GOAL: %s"%(str(traj.points[-1].positions))
            if not cartesian:
                self.send_q(traj.points[-1].positions,acceleration,velocity)
            else:
                self.send_cart(traj.points[-1].positions,acceleration,velocity) ##
            self.set_goal(traj.points[-1].positions)
            start_t = rospy.Time.now()

            # wait until robot is at goal
            #while self.moving:
            while not self.at_goal:
                if (rospy.Time.now() - start_t).to_sec() > 3:
                    return 'FAILURE - timeout'
                rate.sleep()

        goal = FollowJointTrajectoryGoal(trajectory=traj)
        print goal
        self.client.send_goal(goal)
        self.client.wait_for_result()
        print self.client.get_result()

        if self.at_goal:
            return 'SUCCESS - moved to pose'
        else:
            return 'FAILURE - did not reach destination'

    '''
    set teach mode
    '''
    def set_teach_mode_call(self,req,cartesian=False):
        if req.enable == True:

            self.ur.set_freedrive(True)
            self.driver_status = 'TEACH'
            return 'SUCCESS - teach mode enabled'
        else:
            self.ur.set_freedrive(False)
            self.driver_status = 'IDLE'
            return 'SUCCESS - teach mode disabled'

    '''
    send a single joint space position
    '''
    def send_q(self,q,acceleration,velocity):
        pt = JointTrajectoryPoint()
        pt.positions = q

        self.pt_publisher.publish(pt)

    '''
    URX supports Cartesian moves, so we will recover our forward kinematics
    and send a Cartesian pose.
    '''
    def send_cart(self,q,acceleration,velocity):
        if self.simulation:
            pt = JointTrajectoryPoint()
            pt.positions = q

            self.pt_publisher.publish(pt)
        else:
            rospy.logwarn('UR5 cartesian moves are currently unsupported.')
        #else:
        # @TODO(cpaxton) implement UR5 cartesian moves
        #  T = pm.fromMatrix(self.kdl_kin.forward(q))
        #  (angle,axis) = T.M.GetRotAngle()
        #  cmd = list(T.p) + [angle*axis[0],angle*axis[1],angle*axis[2]]
        #  self.ur.movel(cmd,wait=True,acc=acceleration,vel=velocity)

    def handle_tick(self):

        # send out the joint states
        #self.current_joint_positions = self.ur.getj_all()
        #self.q0 = np.array(self.current_joint_positions[0])
        #self.q_v0 = np.array(self.current_joint_positions[1])
        #self.q_a0 = np.array(self.current_joint_positions[2])
        #self.js_publisher.publish(JointState(
        #  header=Header(stamp=rospy.Time.now()),
        #  name=self.joint_names,
        #  position=self.q0,
        #  velocity=self.q_v0,
        #  effort=self.q_a0))
        #self.update_position()

        if self.driver_status in mode.keys():

            if self.driver_status == 'SHUTDOWN':
                self.ur.cleanup()
                self.ur.shutdown()
            elif self.driver_status == 'SERVO':
                pass
            elif self.driver_status == 'IDLE':
                pass
            elif self.driver_status == 'TEACH':
                pass

        else:
            #rospy.logwarn('IIWA mode for %s not specified!'%self.driver_status)
            pass

