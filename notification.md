# Setup AWS-Heidi Notifications

To enable receiving notifications on Slack, Teams, or Chime from Heidi, the setup process comprises follwing essential steps.

# Setting AWS Chatbot

AWS Chatbot is an AWS service that enables DevOps and software development teams to use messaging program chat rooms to monitor and respond to operational events in their AWS Cloud. AWS Chatbot processes AWS service notifications from Amazon Simple Notification Service (Amazon SNS), and forwards them to chat rooms so teams can analyze and act on them immediately, regardless of location.

1. To setup AWS Chatbot with Slack, please visit this this step by step tutorial: [Chatbot-Setup-with-slack](https://docs.aws.amazon.com/chatbot/latest/adminguide/slack-setup.html).
2. To setup AWS Chatbot with Amazon Chime, please visit this this step by step tutorial: [Chatbot-Setup-with-chime](https://docs.aws.amazon.com/chatbot/latest/adminguide/chime-setup.html).
3. To setup AWS Chatbot with Teams, please visit this this step by step tutorial: [Chatbot-Setup-with-teams](https://docs.aws.amazon.com/chatbot/latest/adminguide/teams-setup.html).

# Setting up Filters

By default, all the events going to centerlized event bus will be routed to your notification channel. If you want specific events, you can set filter on SNS subscriptions. 

[Filter-Events](https://docs.aws.amazon.com/sns/latest/dg/sns-subscription-filter-policies.html)