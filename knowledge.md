# Knowledge

A simple guide to what this project does today and what we can build next.

The project is a notification system. Other apps ask it to send a message to a user by email, text message or phone push, and it makes sure the message gets there.

---

## 1. What we have built

### The basics

**Instant reply to the caller**
When an app asks to send a message, the system answers right away that the request is accepted. The real sending happens in the background. This keeps the app fast, even when the email or text provider is slow.

**Background sending with separate workers**
Email, text and push each have their own worker. If one channel is slow or broken, the others keep working normally.

**Retries when sending fails**
If a send fails, the system waits a little and tries again. The wait grows each time, with some randomness added, so many retries do not all hit the provider at the same moment. This matters because networks and providers fail often, and most failures are short lived.

**Dead letter queue**
If a message still fails after the maximum number of tries, it is moved to a separate place instead of being lost. An admin can look at these and send them again later once the problem is fixed.

**No duplicate messages**
The caller can attach a unique key to a request. If the same request arrives twice, because of a network retry for example, the system sends only one message. This matters a lot, because nobody wants two payment alerts or two login codes.

**User preferences**
Each user can switch off any channel, and can set quiet hours, like no messages between 10 at night and 7 in the morning in their own time zone. Messages that arrive in quiet hours are held back and sent later, not thrown away. Urgent messages, like login codes, ignore quiet hours.

**Message templates**
Messages are written once as templates with blanks, like "Hello, your code is ...". The system fills in the blanks for each user. It also checks that nothing is missing, so a half empty message is never sent.

**Status tracking**
Every message has a status that shows where it is: waiting, scheduled, sent, delivered, failed or skipped. The full history of every try is saved, so support teams can answer "what happened to my message?".

**Rate limiting**
The system limits how many messages one user can get in a short time, and how fast it talks to each provider. This protects users from being spammed and protects us from being blocked by providers.

### The extra features

**Priorities**
Messages have three levels: high, normal and low. Login codes go first and marketing goes last. Low priority messages still move along, so they never wait forever.

**Backup provider and circuit breaker**
Each channel has a main provider and a backup. If the main one keeps failing, the system stops using it for a while and switches to the backup. After a short rest it tests the main one again. This keeps messages flowing during provider outages.

**Scheduled messages**
A message can be set to go out at a future time, like a reminder for tomorrow morning.

**Bulk sending**
One message can be sent to a very large group of users, up to a hundred thousand. The system splits the group into small batches and works through them in the background. You can check how far along it is.

### Keeping it healthy

**Logs and metrics**
The system writes clear logs and shares numbers like queue size, failures and retries. A health check tells you if the database and the queue are working. This is how a team notices problems early.

**Safe shutdown**
When a worker is stopped, for an update for example, it finishes the message it is working on first and then exits.

**Protection from crashes**
If a worker crashes in the middle of a job, the job is not lost. After a short time it goes back into the line and another worker picks it up.

**Admin tools**
Admins can see how long each line is and can send failed messages again.

**Delivery confirmation**
A provider can tell the system that a message really reached the user, which moves its status from sent to delivered.

**Easy setup**
One command starts the whole system on a laptop, including a fake inbox to see the emails.

**Automatic checks**
Every time code is pushed to GitHub, the code style is checked and the project is built to make sure nothing is broken.

**Load test and design document**
A load test is ready to measure how much traffic the system can take. A design document explains the thinking, the trade offs, what can go wrong and how to grow the system a hundred times bigger.

---

## 2. What we can build next

### Fix these first

**Recovery for lost jobs**
Today, if the queue service goes down at the exact moment a message is saved, that message can get stuck as waiting. A small background check can find these and put them back in line.

**Shared provider health**
Right now each worker decides on its own when a provider is unhealthy. Sharing that knowledge between all workers would react faster.

**Real speed numbers**
Run the load test and write the results down, like how many messages per second the system handles. This is great proof to show in interviews.

**Proper database upgrades**
Add a safe way to change the database structure over time instead of creating tables at startup.

### Useful features

**Cancel a message**
Let the caller cancel a message that has not been sent yet.

**API keys**
Require a key so only approved apps can use the system.

**Rate limit hints**
Tell the caller how long to wait when they are sending too fast.

**Template versions**
Keep old versions of a template so a change does not affect older requests.

**Many languages**
Pick the message language based on the user's language setting.

**Digest messages**
Combine many small updates into one summary message instead of sending ten separate ones.

**Duplicate content guard**
Skip sending the same message to the same user twice within a short time.

**Unsubscribe link**
Let users switch off messages with one click from the message itself.

**Different rules per message type**
Login codes could retry quickly and give up fast, while marketing messages retry slowly.

**Smarter backup choice**
Pick the best provider based on how well each one has been doing recently.

### Bigger upgrades

**Real providers**
Connect real services for email, text and push, and receive real delivery reports from them.

**A stronger message pipeline**
Move to a bigger message system built for very high traffic, which also keeps order and lets us replay old messages.

**Many customers on one system**
Let different teams or companies use the system with their own templates, limits and keys.

**Request tracing**
Follow one message from the first request all the way to the provider to find slow spots.

**Dashboards and alerts**
Charts and alarms that warn the team when failures rise or messages wait too long.

**Cloud deployment**
Run the system on Kubernetes and add workers automatically when the line gets long.

**Data cleanup by date**
Split old data by date so it can be archived or deleted cheaply.

**Admin screen**
A simple web page to browse messages, failed jobs and bulk sends.

**Live status updates**
Push status changes to a screen as they happen instead of asking again and again.

**Saved audiences**
Save groups of users, like "all premium users", and send to them in bulk.

**Many regions**
Run a full copy in several parts of the world so users get faster, more reliable service.
