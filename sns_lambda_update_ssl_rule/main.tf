module "sns_topic_label" {
  source     = "git::https://github.com/cloudposse/terraform-terraform-label.git?ref=tags/0.1.6"
  name       = "sns"
  namespace  = "${var.namespace}"
  stage      = "${var.stage}"
  attributes = "${compact(concat(var.attributes, list("change", "https", "listener")))}"
}

data "aws_sns_topic" "this" {
  count = "${(1 - var.create_sns_topic) * var.create}"

  name = "${var.sns_topic_name ? var.sns_topic_name: module.sns_topic_name.id}"
}

resource "aws_sns_topic" "this" {
  count = "${var.create_sns_topic * var.create}"

  name = "${var.sns_topic_name ? var.sns_topic_name: module.sns_topic_name.id}"
}

locals {
  sns_topic_arn = "${element(concat(aws_sns_topic.this.*.arn, data.aws_sns_topic.this.*.arn, list("")), 0)}"
}

resource "aws_sns_topic_subscription" "sns_update_ssl" {
  count = "${var.create}"

  topic_arn = "${local.sns_topic_arn}"
  protocol  = "lambda"
  endpoint  = "${aws_lambda_function.update_ssl_rule.0.arn}"
}


resource "aws_lambda_permission" "sns_update_ssl" {
  count = "${var.create}"

  statement_id  = "AllowExecutionFromSNS"
  action        = "lambda:InvokeFunction"
  function_name = "${aws_lambda_function.update_ssl_rule.0.function_name}"
  principal     = "sns.amazonaws.com"
  source_arn    = "${local.sns_topic_arn}"
}

data "null_data_source" "lambda_file" {
  inputs {
    filename = "${substr("${path.module}/functions/update_ssl_rule.py", length(path.cwd) + 1, -1)}"
  }
}

data "null_data_source" "lambda_archive" {
  inputs {
    filename = "${substr("${path.module}/functions/update_ssl_rule.zip", length(path.cwd) + 1, -1)}"
  }
}

data "archive_file" "update_ssl_rule" {
  count = "${var.create}"

  type        = "zip"
  source_file = "${data.null_data_source.lambda_file.outputs.filename}"
  output_path = "${data.null_data_source.lambda_archive.outputs.filename}"
}


resource "aws_lambda_function" "update_ssl_rule" {
  count = "${var.create}"

  filename = "${data.archive_file.update_ssl_rule.0.output_path}"

  function_name = "${var.lambda_function_name}"

  role             = "${aws_iam_role.lambda.arn}"
  handler          = "update_ssl_rule.lambda_handler"
  source_code_hash = "${data.archive_file.update_ssl_rule.0.output_base64sha256}"
  runtime          = "python3.6"
  timeout          = 30
  kms_key_arn      = "${var.kms_key_arn}"

  environment {
    variables = {
      ELB_REGION              = "${var.elb_region}"
      PRODUCTION_LISTENER_ARN = "${var.prod_listener_arn}"
      SSL_LISTENER_ARN        = "${var.ssl_listener_arn}"
    }
  }

  lifecycle {
    ignore_changes = [
      "filename",
      "last_modified",
    ]
  }
}