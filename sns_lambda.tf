locals {
  ssl_enabled = "${var.alb_ssl_listener_arn ? true : false}"
}

data "aws_lb_listener" "ssl_listener" {
  arn = "${var.alb_ssl_listener_arn}"
}

module "update_ssl_rule" {
  source         = "sns_lambda_update_ssl_rule"
  create         = "${local.ssl_enabled}"
  name           = "${var.name}"
  namespace      = "${var.namespace}"
  stage          = "${var.stage}"
  attributes     = "${var.attributes}"
  elb_region     = "${var.aws_logs_region}"

  ecs_cluster_name  = "${var.ecs_cluster_name}"
  prod_listener_arn = "${var.alb_prod_listener_arn}"
  ssl_listener_arn  = "${var.alb_ssl_listener_arn}"
}
