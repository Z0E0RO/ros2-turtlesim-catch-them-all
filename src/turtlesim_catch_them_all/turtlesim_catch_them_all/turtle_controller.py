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

        self.pose_ = None
        self.alive_turtles_ = []
        self.target_turtle_ = None
        self.catch_in_progress_ = False

        self.pose_subscriber_ = self.create_subscription(
            Pose,
            "/turtle1/pose",
            self.callback_turtle_pose,
            10
        )

        self.get_logger().info(
            "Position subscriber has been created"
        )

        self.cmd_vel_publisher_ = self.create_publisher(
            Twist,
            "/turtle1/cmd_vel",
            10
        )

        self.alive_turtles_subscriber_ = self.create_subscription(
            TurtleArray,
            "/alive_turtles",
            self.callback_alive_turtles,
            10
        )

        self.catch_turtle_client_ = self.create_client(
            CatchTurtle,
            "/catch_turtle"
        )

        self.control_loop_timer_ = self.create_timer(
            0.01,
            self.control_loop
        )


    def callback_turtle_pose(self, pose: Pose):

        self.pose_ = pose

        # If turtles arrived before the first pose message,
        # select a target now.
        if (
            self.target_turtle_ is None
            and len(self.alive_turtles_) > 0
        ):
            self.get_closest_turtle()


    def callback_alive_turtles(
        self,
        alive_turtles: TurtleArray
    ):

        self.alive_turtles_ = alive_turtles.turtles

        if len(self.alive_turtles_) == 0:

            self.target_turtle_ = None
            self.catch_in_progress_ = False
            return

        # Don't calculate distances until turtle1 pose exists.
        if self.pose_ is None:
            return

        # If the current target was caught and removed,
        # allow a new catch operation.
        if self.target_turtle_ is not None:

            target_still_alive = False

            for turtle in self.alive_turtles_:

                if turtle.name == self.target_turtle_.name:
                    target_still_alive = True
                    break

            if not target_still_alive:
                self.target_turtle_ = None
                self.catch_in_progress_ = False

        # Choose the closest available turtle.
        if self.target_turtle_ is None:
            self.get_closest_turtle()


    def control_loop(self):

        if self.pose_ is None or self.target_turtle_ is None:
            return

        target_x = self.target_turtle_.x
        target_y = self.target_turtle_.y

        dist_x = target_x - self.pose_.x
        dist_y = target_y - self.pose_.y

        distance = math.sqrt(
            dist_x * dist_x +
            dist_y * dist_y
        )

        cmd = Twist()

        if distance > 0.5:

            cmd.linear.x = 2.0 * distance

            target_theta = math.atan2(
                dist_y,
                dist_x
            )

            final_theta = (
                target_theta -
                self.pose_.theta
            )

            if final_theta > math.pi:
                final_theta -= 2.0 * math.pi

            elif final_theta < -math.pi:
                final_theta += 2.0 * math.pi

            cmd.angular.z = 6.0 * final_theta

        else:

            cmd.linear.x = 0.0
            cmd.angular.z = 0.0

            # Send only ONE catch request.
            if not self.catch_in_progress_:

                self.catch_in_progress_ = True

                catch_request = CatchTurtle.Request()
                catch_request.name = self.target_turtle_.name

                future = self.catch_turtle_client_.call_async(
                    catch_request
                )

                future.add_done_callback(
                    self.callback_catch_request
                )

        self.cmd_vel_publisher_.publish(cmd)


    def callback_catch_request(self, future):

        try:

            response = future.result()

            if not response.success:

                self.get_logger().warn(
                    "Catch request failed"
                )

                self.catch_in_progress_ = False

        except Exception as error:

            self.get_logger().error(
                "Catch service error: "
                + str(error)
            )

            self.catch_in_progress_ = False


    def get_closest_turtle(self):

        if self.pose_ is None:
            return

        closest_distance = float("inf")
        self.target_turtle_ = None

        for turtle in self.alive_turtles_:

            dist_x = turtle.x - self.pose_.x
            dist_y = turtle.y - self.pose_.y

            distance = math.sqrt(
                dist_x * dist_x +
                dist_y * dist_y
            )

            if distance < closest_distance:

                closest_distance = distance
                self.target_turtle_ = turtle

        if self.target_turtle_ is not None:

            self.get_logger().info(
                f"Closest turtle: "
                f"{self.target_turtle_.name}, "
                f"distance: {closest_distance:.2f}"
            )


def main(args=None):

    rclpy.init(args=args)

    node = TurtleController()

    rclpy.spin(node)

    rclpy.shutdown()


if __name__ == "__main__":
    main()
