import json, boto3

def lambda_handler(event, context):
    region = os.environ['ELB_REGION']
    elbv2_client = boto3.client('elbv2', region_name=region)

    # Get HTTP Target Group.
    http_listener_arn = os.environ['PRODUCTION_LISTENER_ARN']
    http_listener = elbv2_client.describe_rules( ListenerArn=http_listener_arn)
    http_target_group_arn = http_listener['Rules'][0]['Actions'][0]['TargetGroupArn']

    # Get HTTPS listener rules.
    https_listener_arn = os.environ['SSL_LISTENER_ARN']
    https_listener = elbv2_client.describe_rules(ListenerArn=https_listener_arn)
    https_listener_rules = https_listener['Rules']

    results = {}

    i = 0
    while i < len(https_listener_rules):
        rule_actions = https_listener_rules[i]['Actions']

        rule_modded = 0
        n = 0
        while n < len(rule_actions):
            if rule_actions[n]['Type'] == "forward":
                rule_actions[n]['TargetGroupArn']=http_target_group_arn
                rule_modded=1


        if rule_modded==1:
            results[https_listener_rules[i]['RuleArn']] = elbv2_client.modify_rule(
                RuleArn=https_listener_rules[i],
                Actions=rule_actions
            )

        i +=1

    return results
