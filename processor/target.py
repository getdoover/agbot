#!/usr/bin/python3
import os, sys, time, json, traceback

## This is the definition for a tiny lambda function
## Which is run in response to messages processed in Doover's 'Channels' system

## In the doover_config.json file we have defined some of these subscriptions
## These are under 'processor_deployments' > 'tasks'


## You can import the pydoover module to interact with Doover based on decisions made in this function
## Just add the current directory to the path first

## attempt to delete any loaded pydoover modules that persist across lambdas
if 'pydoover' in sys.modules:
    del sys.modules['pydoover']
try: del pydoover
except: pass
try: del pd
except: pass

# sys.path.append(os.path.dirname(__file__))
import pydoover as pd


class target:

    def __init__(self, *args, **kwargs):

        self.kwargs = kwargs
        ### kwarg
        #     'agent_id' : The Doover agent id invoking the task e.g. '9843b273-6580-4520-bdb0-0afb7bfec049'
        #     'access_token' : A temporary token that can be used to interact with the Doover API .e.g 'ABCDEFGHJKLMNOPQRSTUVWXYZ123456890',
        #     'api_endpoint' : The API endpoint to interact with e.g. "https://my.doover.com",
        #     'package_config' : A dictionary object with configuration for the task - as stored in the task channel in Doover,
        #     'msg_obj' : A dictionary object of the msg that has invoked this task,
        #     'task_id' : The identifier string of the task channel used to run this processor,
        #     'log_channel' : The identifier string of the channel to publish any logs to


    ## This function is invoked after the singleton instance is created
    def execute(self):

        start_time = time.time()

        self.create_doover_client()

        self.add_to_log( "kwargs = " + str(self.kwargs) )
        self.add_to_log( str( start_time ) )

        self.ui_state_channel = self.cli.get_channel(
            channel_name="ui_state",
            agent_id=self.kwargs['agent_id'] )
        
        self.uplink_recv_channel = pd.channel(
            api_client=self.cli.api_client,
            agent_id=self.kwargs['agent_id'],
            channel_name='agbot-webhook-recv',
        )

        try:
            
            ## Do any processing you would like to do here
            message_type = None
            if 'message_type' in self.kwargs['package_config'] and 'message_type' is not None:
                message_type = self.kwargs['package_config']['message_type']

            if message_type == "DEPLOY":
                self.deploy()

            if message_type == "DOWNLINK":
                self.downlink()

            if message_type == "UPLINK":
                self.uplink()

        except Exception as e:
            self.add_to_log("ERROR attempting to process message - " + str(e))
            self.add_to_log(traceback.format_exc())

        self.complete_log()



    def deploy(self):
        ## Run any deployment code here
        
        ## Get the deployment channel
        ui_obj = {
            "state" : {
                "type" : "uiContainer",
                "displayString" : "",
                "children" : {
                    "significantEvent": {
                        "type": "uiAlertStream",
                        "name": "significantEvent",
                        "displayString": "Notify me of any problems"
                    },
                    "waterLevel" : {
                        "type" : "uiVariable",
                        "varType" : "float",
                        "name" : "waterLevel",
                        "displayString" : "Water Level (%)",
                        "form": "radialGauge",
                        "ranges": [
                            {
                                "label" : "Low",
                                "min" : 0,
                                "max" : 40,
                                "colour" : "yellow",
                                "showOnGraph" : True
                            },
                            {
                                "label" : "Half",
                                "min" : 40,
                                "max" : 80,
                                "colour" : "blue",
                                "showOnGraph" : True
                            },
                            {
                                "label" : "Full",
                                "min" : 80,
                                "max" : 100,
                                "colour" : "green",
                                "showOnGraph" : True
                            }
                        ]
                    },
                    "numLitres" : {
                        "type" : "uiVariable",
                        "varType" : "float",
                        "name" : "numLitres",
                        "displayString" : "Number of litres (L)"
                    },
                    "batteryVoltage" : {
                        "type" : "uiVariable",
                        "varType" : "float",
                        "name" : "batteryVoltage",
                        "displayString" : "Battery Voltage"
                    },
                    "details_submodule": {
                        "type": "uiSubmodule",
                        "name": "details_submodule",
                        "displayString": "Details",
                        "children": {
                            "inputMax": {
                                "type": "uiFloatParam",
                                "name": "inputMax",
                                "displayString": "Max Level (cm)",
                                "min": 0,
                                "max": 999
                            },
                            "inputLowLevel": {
                                "type": "uiFloatParam",
                                "name": "inputLowLevel",
                                "displayString": "Low level alarm (%)",
                                "min": 0,
                                "max": 99
                            },
                            "battAlarmLevel": {
                                "type": "uiFloatParam",
                                "name": "battAlarmLevel",
                                "displayString": "Battery Alarm (%)",
                                "min": 0,
                                "max": 100
                            },
                            "tankCapacity": {
                                "type": "uiFloatParam",
                                "name": "tankCapacity",
                                "displayString": "Tank capacity (L)",
                                "min": 0,
                                "max": 1000000
                            },
                        }
                    }
                }
            }
        }

        self.ui_state_channel.publish(
            msg_str=json.dumps(ui_obj)
        )


    def downlink(self):
        ## Run any downlink processing code here
        pass

    def uplink(self):
        ui_cmds_channel = self.cli.get_channel(
            channel_name="ui_cmds",
            agent_id=self.kwargs['agent_id']
        )

        ## Run any uplink processing code here
        uplink_aggregate = self.uplink_recv_channel.get_aggregate()
        self.add_to_log(uplink_aggregate)
        self.ui_state_channel.publish(
            msg_str=json.dumps({
                "state" : {
                    "children" : {
                        "waterLevel": {
                            "currentValue": self.get_water_level_percentage(ui_cmds_channel, uplink_aggregate)
                        },
                        "batteryVoltage": {
                            "currentValue": int(uplink_aggregate["DeviceBatteryVoltage"])
                        },
                        "numLitres": {
                            "currentValue": self.get_water_litres(ui_cmds_channel, uplink_aggregate)
                        }
                    }
                }
            })
        )

        self.assess_warnings(ui_cmds_channel, self.ui_state_channel)

        pass

    def get_water_level_percentage(self, cmds_channel, uplink_aggregate):
        cmds_obj = cmds_channel.get_aggregate()
        
        sensor_max = 250
        
        try:
            sensor_max = cmds_obj['cmds']['inputMax']
        except Exception as e:
            self.add_to_log("Could not get sensor max - " + str(e))

        water_level = 0
        try:
            water_level = uplink_aggregate["AssetDepth"] * 100
        except:
            self.add_to_log("Could not get current water depth.")
        
        return (100 / sensor_max) * water_level 

    def get_water_litres(self, cmds_channel, uplink_aggregate):
        cmds_obj = cmds_channel.get_aggregate()
        max_tank_size = cmds_obj['cmds']['tankCapacity']
        water_level_percentage = self.get_water_level_percentage(cmds_channel, uplink_aggregate)

        return max_tank_size * water_level_percentage / 100

    def assess_warnings(self, cmds_channel, state_channel):
        cmds_obj = cmds_channel.get_aggregate()
        
        level_alarm = None
        try: level_alarm = cmds_obj['cmds']['inputLowLevel']
        except Exception as e: self.add_to_log("Could not get level alarm")

        battery_alarm = None
        try: battery_alarm = cmds_obj['cmds']['battAlarmLevel']
        except Exception as e: self.add_to_log("Could not get battery alarm")
        
        state_obj = state_channel.get_aggregate()

        curr_level = None
        try: curr_level = state_obj['state']['children']['waterLevel']['currentValue']
        except Exception as e: self.add_to_log("Could not get current level - " + str(e))

        curr_battery_level = None
        try: curr_battery_level = state_obj['state']['children']['batteryLevel']['currentValue']
        except Exception as e: self.add_to_log("Could not get current battery level - " + str(e))

        notifications_channel = pd.channel(
            api_client=self.cli.api_client,
            agent_id=self.kwargs['agent_id'],
            channel_name='significantEvent',
        )
        activity_log_channel = pd.channel(
            api_client=self.cli.api_client,
            agent_id=self.kwargs['agent_id'],
            channel_name='activity_logs',
        )
        last_notification_age = self.get_last_notification_age()

        level_warning = None
        if level_alarm is not None and curr_level is not None and curr_level < level_alarm:
            self.add_to_log("Sensor level is low")

            level_warning = {
                "type": "uiWarningIndicator",
                "name": "levelLowWarning",
                "displayString": "Level Low"
            }
            
            prev_level = self.get_previous_level(state_channel, "waterLevel")
            if prev_level is not None and prev_level > level_alarm:
                if last_notification_age is None or last_notification_age > (12 * 60 * 60):
                    self.add_to_log("Sending low level notification")
                    notifications_channel.publish(
                        msg_str="Level is getting low"
                    )
                    activity_log_channel.publish(json.dumps({
                        "activity_log" : {
                            "action_string" : "Level is getting low"
                        }
                    }))
                else:
                    self.add_to_log("Not sending low level notification as already sent notification recently")


        batt_warning = None
        if battery_alarm is not None and curr_battery_level is not None and curr_battery_level < battery_alarm:
            self.add_to_log("Battery level is low")
            
            batt_warning = {
                "type": "uiWarningIndicator",
                "name": "battLowWarning",
                "displayString": "Battery Low"
            }

            prev_level = self.get_previous_level(state_channel, "batteryLevel")
            if prev_level is not None and prev_level > battery_alarm:
                if last_notification_age is None or last_notification_age > (12 * 60 * 60):
                    self.add_to_log("Sending low battery notification")
                    notifications_channel.publish(
                        msg_str="Battery is getting low"
                    )
                    activity_log_channel.publish(json.dumps({
                        "activity_log" : {
                            "action_string" : "Battery is getting low"
                        }
                    }))
                else:
                    self.add_to_log("Not sending low battery notification as already sent notification recently")


        ## Assess status icon
        status_icon = None
        if curr_level is None:
            status_icon = "off"
        else:
            idle_icon_level = 60
            if level_alarm is not None:
                idle_icon_level = (100 + level_alarm) / 2   ## midpoint of full and alarm level
            if curr_level < idle_icon_level:
                status_icon = "idle"


        msg_obj = {
            "state" : {
                "children" : {
                    "battLowWarning": batt_warning,
                    "levelLowWarning": level_warning
                },
                "statusIcon" : status_icon
            }
        }

        state_channel.publish(
            msg_str=json.dumps(msg_obj),
            save_log=False
        )

    def get_last_notification_age(self):
        notifications_channel = pd.channel(
            api_client=self.cli.api_client,
            agent_id=self.kwargs['agent_id'],
            channel_name='significantEvent',
        )
        notifications_messages = notifications_channel.get_messages()

        last_notification_age = None
        if len(notifications_messages) > 0:
            try:
                last_notif_message = notifications_messages[0].update()
                last_notification_age = last_notif_message['current_time'] - last_notif_message['timestamp']
            except Exception as e:
                self.add_to_log("Could not get age of last notification - " + str(e))
                pass  

        return last_notification_age

    def get_previous_level(self, state_channel, key):
        state_messages = state_channel.get_messages()

        ## Search through the last few messages to find the last battery level
        if len(state_messages) < 3:
            self.add_to_log("Not enough data to get previous levels")
            return None

        ### The device published a new message,
        # Then we just published a message to update rssi, snr, etc
        # so we need the message one before that
        i = 2
        prev_level = None
        while prev_level is None and i < 10 and i < len(state_messages):
            try:
                prev_state_payload = json.loads( state_messages[i].get_payload() )
                prev_level = prev_state_payload['state']['children'][key]['currentValue']
                self.add_to_log("Found previous level of " + str(prev_level) + ", " + str(i) + " messages ago : " + str(state_messages[i].message_id))
            except Exception as e:
                pass
            i = i + 1

        if prev_level is None:
            self.add_to_log("Could not get previous level - " + str(e))
        
        return prev_level 


    def create_doover_client(self):
        self.cli = pd.doover_iface(
            agent_id=self.kwargs['agent_id'],
            access_token=self.kwargs['access_token'],
            endpoint=self.kwargs['api_endpoint'],
        )

    def add_to_log(self, msg):
        if not hasattr(self, '_log'):
            self._log = ""
        self._log = self._log + str(msg) + "\n"

    def complete_log(self):
        if hasattr(self, '_log') and self._log is not None:
            log_channel = self.cli.get_channel( channel_id=self.kwargs['log_channel'] )
            log_channel.publish(
                msg_str=self._log
            )
