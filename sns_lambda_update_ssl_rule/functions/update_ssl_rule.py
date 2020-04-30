import os
import json, boto3

def lambda_handler(event, context):
    print("Trigger Event: ")
    print(event)
    region = os.environ['REGION']
    elbv2_client = boto3.client('elbv2', region_name=region)

    available_target_groups = os.environ['AVAILABLE_TARGET_GROUPS']
    arr_available_target_groups = available_target_groups.split(',')

    # Get HTTP Target Group.
    http_listener_arn = os.environ['HTTP_LISTENER_ARN']
    http_listener = elbv2_client.describe_rules( ListenerArn=http_listener_arn)
    http_target_group_arn = get_current_http_target_group(http_listener['Rules'], arr_available_target_groups)

    if http_target_group_arn==False:
        print("Could not identify the target arn")
        return False

    print("Current HTTP target group: ")
    print(http_target_group_arn)

    # Get HTTPS listener rules.
    https_listener_arn = os.environ['SSL_LISTENER_ARN']
    https_listener = elbv2_client.describe_rules(ListenerArn=https_listener_arn)
    https_listener_rules = https_listener['Rules']

    print("Current HTTPS target group: ")
    https_target_group_arn = get_current_http_target_group(https_listener['Rules'], arr_available_target_groups)
    print(https_target_group_arn)

    results = {}
    i = 0
    while i < len(https_listener_rules):

        # Skip default rule
        if https_listener_rules[i]['IsDefault']==True:
            i +=1
            continue

        actions = https_listener_rules[i]['Actions']
        actions, modify = process_actions(actions, http_target_group_arn, arr_available_target_groups)

        if modify==1:
            print("Updating SSL listener rules..")
            rule_arn = https_listener_rules[i]['RuleArn']
            results[rule_arn] = modify_rules(elbv2_client, rule_arn, actions)

        i +=1

    # For ECS After Allow Test Traffic hook
    print(results)
    send_codedeploy_validation_status(event, results)

    return results

# Returns the current B/G target group from a list of lister rules.
def get_current_http_target_group(http_listener_rules, arr_available_target_groups):

    i=0
    while i < len(http_listener_rules):

        # Continue if default listener rule.
        if http_listener_rules[i]['IsDefault']==True:
            i +=1
            continue

        actions = http_listener_rules[i]['Actions']
        n=0

        while n<len(actions):
            try:
                for tg in actions[n]['ForwardConfig']['TargetGroups']:
                    if tg['TargetGroupArn'] in arr_available_target_groups and (tg['Weight'] is 100 or tg['Weight'] is 1) :
                        return tg['TargetGroupArn']
            except Exception as e:
                print(e)
            n +=1

        i +=1

    return False


def process_actions(actions, http_target_group_arn, arr_available_target_groups):
    modify = 0
    for ak, action in enumerate(actions):
        try:
            if action['Type'] == "forward" and check_target_update(action['TargetGroupArn'], arr_available_target_groups):
                actions[ak]['TargetGroupArn']=http_target_group_arn
                for tgk, target_group in enumerate(action['ForwardConfig']['TargetGroups']):
                    if check_target_update(target_group['TargetGroupArn'], arr_available_target_groups):
                        actions[ak]['ForwardConfig']['TargetGroups'][tgk]['TargetGroupArn']=http_target_group_arn
                modify=1
        except Exception as e:
            print(e)

    return (actions), modify

# Check old target group is associated w/out available target and different.
# Be wary I found its possible the Listener rule is updated at the initial Ready Stage.
# DO NOT TRY COMPARING OLD AN NEW, SIMPLY ALWAYS UPDATE TO MATCH HTTP IF ONE OF THE AVAILABLE TARGETS
def check_target_update(old_target_group, arr_available_target_groups):

    return old_target_group in arr_available_target_groups


# Sends notification to CodeDeploy on hook status...
def send_codedeploy_validation_status(event, results):
    region = os.environ['REGION']
    codedeploy_client = boto3.client('codedeploy', region_name=region)
    status = ('Failed', 'Succeeded')[len(results) > 0]
    print(status)

    try:
        return codedeploy_client.put_lifecycle_event_hook_execution_status(
            deploymentId=event['DeploymentId'],
            lifecycleEventHookExecutionId=event['LifecycleEventHookExecutionId'],
            status=status
        )
    except Exception as e:
        print("Recoverable Exception: ")
        print(e)
        return False


def modify_rules(elbv2_client, arn, actions):
    try:
        return elbv2_client.modify_rule(
            RuleArn=arn,
            Actions=actions
        )
    except Exception as e:
        print(e)
