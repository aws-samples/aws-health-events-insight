# Setup AWS-Heidi Notifications

To enable receiving notifications on Slack or Teams from AWS-Heidi, the setup process comprises two essential steps.
1. Setting AWS Chatbot
2. Configure AWS notifications

# Setting AWS Chatbot
AWS Chatbot is an AWS service that enables DevOps and software development teams to use messaging program chat rooms to monitor and respond to operational events in their AWS Cloud. AWS Chatbot processes AWS service notifications from Amazon Simple Notification Service (Amazon SNS), and forwards them to chat rooms so teams can analyze and act on them immediately, regardless of location.

1. To setup AWS Chatbot with slack, please visit this this step by step tutorial: ![Chatbot-Setup-with-slack](https://docs.aws.amazon.com/chatbot/latest/adminguide/slack-setup.html).
2. To setup AWS Chatbot with Amazon Chime, please visit this this step by step tutorial: ![Chatbot-Setup-with-chime](https://docs.aws.amazon.com/chatbot/latest/adminguide/chime-setup.html).
3. To setup AWS Chatbot with slack, please visit this this step by step tutorial: ![Chatbot-Setup-with-teams](https://docs.aws.amazon.com/chatbot/latest/adminguide/teams-setup.html).

# Configure AWS notifications
1. Access the AWS user notification section.
2. Choose the option to create notification configurations and enter a name and description.
3. Within the event section, select "health" as the AWS service name and choose "specific health events" as the event type.
4. Pick the region where your central account setup is deployed.
5. Configure AWS Chatbot as the delivery channel and select the AWS Chatbot instance set up in the previous step titled "Setting AWS Chatbot."
