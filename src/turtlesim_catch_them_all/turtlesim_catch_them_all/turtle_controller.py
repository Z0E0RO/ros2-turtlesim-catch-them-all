import rclpy
from rclpy.node import Node
from turtlesim.msg import Pose
from geometry_msgs.msg import Twist
import math
from custom_interfaces.msg import TurtleArray
from custom_interfaces.srv import CatchTurtle

class TurtleController(Node):
	def __init__(self):
		super().__init__("turtle_controller")
		self.pose_subscriber_ = self.create_subscription(Pose, "/turtle1/pose", self.callback_turtle_pose, 10)
		self.get_logger().info("Position subscriber has been created")
		self.pose_ = Pose()
		self.pose_ = None
		self.alive_turtles_ = []
		self.target_turtle_ = None 
		
		# self.target_x = 8.0
		# self.target_y = 2.0
		self.cmd_vel_publisher_ = self.create_publisher(Twist, "/turtle1/cmd_vel", 10)
		self.alive_turtles_subscriber_ = self.create_subscription(TurtleArray, "alive_turtles", self.callback_alive_turtles, 10)
		self.catch_turtle_client_ = self.create_client(CatchTurtle, "catch_turtle")
		self.control_loop_timer_ = self.create_timer(0.01, self.control_loop)
		
	def callback_turtle_pose(self, pose:Pose):
		self.pose_ = pose
		
	def callback_alive_turtles(self, alive_turtles:TurtleArray):
		self.alive_turtles_ = alive_turtles.turtles
		if len(self.alive_turtles_) > 0:
			self.get_closest_turtle()
		
	def control_loop(self):
		if self.pose_ is None or self.target_turtle_ is None:
			return
		
		target_x = self.target_turtle_.x
		target_y = self.target_turtle_.y
		dist_x = target_x - self.pose_.x
		dist_y = target_y - self.pose_.y
		distance = math.sqrt(dist_x * dist_x + dist_y * dist_y)
		
		cmd = Twist()
		if distance > 0.5:
			cmd.linear.x = 2*distance
			
			target_theta = math.atan2(dist_y, dist_x)
			final_theta = target_theta - self.pose_.theta
			if final_theta > math.pi:
				final_theta -= 2*math.pi
			elif final_theta < -math.pi:
				final_theta += 2*math.pi
			cmd.angular.z = 6*final_theta
		else:
			cmd.linear.x = 0.0
			cmd.angular.z = 0.0
			
			kill_request = CatchTurtle.Request()
			kill_request.name = self.target_turtle_.name
			future = self.catch_turtle_client_.call_async(kill_request)
			future.add_done_callback(self.callback_kill_request)
			
		self.cmd_vel_publisher_.publish(cmd)
		
	def callback_kill_request(self, future):
		pass
		
	def get_closest_turtle(self):
		closest_distance = float("inf")
		
		for turtle in self.alive_turtles_:
			dist_x = turtle.x - self.pose_.x
			dist_y = turtle.y - self.pose_.y
			distance = math.sqrt(dist_x*dist_x + dist_y*dist_y)
			if distance < closest_distance:
				closest_distance = distance
				self.target_turtle_ = turtle
		
def main(args=None):
	rclpy.init(args=args)
	node = TurtleController()
	rclpy.spin(node)
	rclpy.shutdown()
	
if __name__ == "__main__":
	main()
		
