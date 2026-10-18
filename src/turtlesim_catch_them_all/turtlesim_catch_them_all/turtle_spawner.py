import rclpy
from rclpy.node import Node
from turtlesim.srv import Spawn
from turtlesim.srv import Kill
import random
import math
from custom_interfaces.msg import Turtle
from custom_interfaces.msg import TurtleArray
from functools import partial
from custom_interfaces.srv import CatchTurtle

class TurtleSpawnerNode(Node):
    def __init__(self):
        super().__init__("turtle_spawner")
        self.turtle_name_prefix_ = "turtle"
        self.turtle_counter_ = 1
        self.alive_turtles_ = []
        self.alive_turtle_publisher_ = self.create_publisher(TurtleArray, "alive_turtles", 10)

        self.client_ = self.create_client(Spawn, "/spawn")
        self.kill_client_ = self.create_client(Kill, "/kill")
        self.catch_turtle_service_ = self.create_service(CatchTurtle, "catch_turtle", self.callback_catch_turtle)
        while not self.client_.wait_for_service(5.0):
            self.get_logger().warn("Waiting for the service")
        while not self.kill_client_.wait_for_service(5.0):
        	self.get_logger().warn("Waiting for the service")
            
        self.spawn_timer_ = self.create_timer(1.0, self.call_spawn)
        
    def alive_turtles_publisher(self):
    	alive_turtles = TurtleArray()
    	alive_turtles.turtles = self.alive_turtles_
    	self.alive_turtle_publisher_.publish(alive_turtles)   

    def call_spawn(self):
        x = random.uniform(0.0, 11.0)
        y = random.uniform(0.0, 11.0)
        theta = random.uniform(0.0, 2*math.pi)
        self.turtle_counter_ += 1
        name = self.turtle_name_prefix_ + str(self.turtle_counter_)
        
        request = Spawn.Request()
            
        request.x = x
        request.y = y
        request.theta = theta
        request.name = name
        future = self.client_.call_async(request)
        future.add_done_callback(partial(self.callback_call_spawn_service, request=request))
        
    def callback_call_spawn_service(self, future, request: Spawn.Request):
    	response: Spawn.Response = future.result()
    	if response.name != "":
    		self.get_logger().info("New alive turtle " + response.name)
    		new_turtle = Turtle()
    		new_turtle.name = response.name
    		new_turtle.x = request.x
    		new_turtle.y = request.y
    		new_turtle.theta = request.theta
    		self.alive_turtles_.append(new_turtle)
    		self.alive_turtles_publisher()
    		
    def callback_catch_turtle(self, request:CatchTurtle.Request, response:CatchTurtle.Response):
    	turtle_found = False
    	for turtle in self.alive_turtles_:
    		if request.name == turtle.name:
    			turtle_found = True
    			break

    	if not turtle_found:
    		self.get_logger().warn("Turtle not found " + request.name)
    		response.success = False
    		return response
    	
    	kill_request = Kill.Request()
    	kill_request.name = request.name
    	future = self.kill_client_.call_async(kill_request)
    	future.add_done_callback(partial(self.callback_kill_turtle, turtle_name = request.name))
    	response.success = True
    	return response
    	
    def callback_kill_turtle(self, future, turtle_name):
    	for turtle in self.alive_turtles_:
    		if turtle_name == turtle.name:
    			self.alive_turtles_.remove(turtle)
    			break
    	self.alive_turtles_publisher()
        

def main(args=None):
    rclpy.init(args=args)
    node = TurtleSpawnerNode()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == "__main__":
    main()
