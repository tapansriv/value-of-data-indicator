# Setting up AWS access for the VDI Spark experiment

Tapan's AWS user can already see resources, but it can't grant the machines their
own identity. That step, and a few related ones, need an account administrator. The
attached file, `vdi-spark-scale-setup.yaml`, does all of them at once.

## What it grants, and what it doesn't

**Tapan will be able to:**
- Launch, stop and delete machines of any type, and set up their networking, but
  only in the Ohio region. He plans to use `r7g.2xlarge`; allowing any type means
  he can switch without asking you again. 
- Connect to machines in the Ohio region with SSH and
  routed through AWS Systems Manager, so no SSH port is open to the internet.
- Use S3 across all buckets in the account.
- See the account's bills, invoices and costs (read-only), plus quotas and
  prices, and request a quota increase. He can't change payment or billing
  settings, or change or delete the budget alert you set up. The intended
  request quota is 248 vCPUs so that multiple overhead experiments can run in
  parallel. 

**It also sets up** a monthly budget alert. You'll get an email when the account's
spending passes 50% and 80% of the threshold you choose, or when AWS forecasts it
will exceed it.

## Before you start

- Sign in to the AWS console (<https://console.aws.amazon.com>) with an
  account that has **administrator** access.
- The `vdi-spark-scale-setup.yaml` file

## Steps

**1. Switch the region to Ohio.**
In the top-right corner of the console, next to your account name, there's a region
menu. Choose **US East (Ohio) us-east-2**. *This is the most common mistake. If you
skip it, step 6 will fail with a message saying to switch to Ohio.*

**2. Open CloudFormation.**
Type **CloudFormation** in the search bar at the top and click it. Then click
**Create stack**, and if asked, choose **With new resources (standard)**.

**3. Upload the file.**
Under *Specify template*, choose **Upload a template file**, click **Choose file**,
select `vdi-spark-scale-setup.yaml`, and click **Next**.

**4. Fill in the fields.**
- **Stack name:** `vdi-spark-scale`
- **Your email address, for budget alerts:** your email.
- **A second email for budget alerts:** Tapan's email, so he sees the alerts too.
- **Monthly alert threshold:** leave it at `800` unless you want a different number.
- Leave the field under *"Leave these as they are"* unchanged.

Click **Next**.

**5. Skip the options page.**
The *Configure stack options* page needs no changes. Scroll down and click **Next**.

**6. Acknowledge and create.**
On the review page, scroll to the bottom and tick the box that says *"I acknowledge
that AWS CloudFormation might create IAM resources with custom names."* It's required,
because the file creates a role and a permission policy. Click **Submit**.

**7. Wait for the green status.**
The status starts as `CREATE_IN_PROGRESS`. After 1–3 minutes it should change to
**`CREATE_COMPLETE`** in green. That's it: tell Tapan it's done.

## If something goes wrong

If the status turns red (`ROLLBACK_COMPLETE` or `CREATE_FAILED`):

1. Click the **Events** tab, find the **first** row marked `CREATE_FAILED`, and send
   Tapan a screenshot of its *Status reason*.
2. Click **Delete** to remove the failed attempt before trying again.

**One thing to know in advance:** this AWS account is part of an **AWS
Organization**, which probably means the university or a department manages it
centrally. If the error mentions *"explicit deny"* or a *"service control
policy"*, that's a restriction set by the organization's managers, and neither you nor
Tapan can override it. Forward the screenshot to whoever set up the account, likely
central IT or the research computing office.

## If Tapan can't see costs afterwards

AWS keeps billing pages closed to everyone but the account owner until one setting is
switched on:

1. Sign in as the root user (the email address the account was created with).
2. Click the account name at the top right → **Account**.
3. Find **IAM user and role access to Billing information**, click **Edit**, tick
   **Activate IAM Access**, and click **Update**.

If that setting isn't there, or costs are still hidden, the university's AWS
Organization probably controls it. If so we can probably skip the cost
visibility step since it's not critical for running the experiments since
otherwise it would require talking to some university admin/IT. 
