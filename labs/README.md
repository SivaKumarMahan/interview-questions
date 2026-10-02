# Hands-On Labs

Small labs you can run on a laptop to practise the troubleshooting and build skills that interviewers ask about. Each lab has its own README with the steps, the files you need, and an "Expected result" section, so you can check your work.

| Lab | What you do | Tools | Time |
| --- | --- | --- | --- |
| [01-kind-broken-deployment](01-kind-broken-deployment/) | Fix a Deployment with a `CrashLoopBackOff` and a failing readiness probe | Docker, kind, kubectl | 30 min |
| [02-opentofu-localstack](02-opentofu-localstack/) | Create an S3 state bucket, use the S3 backend, and watch state locking | Docker, OpenTofu (or Terraform) | 30 min |
| [03-docker-multistage-optimization](03-docker-multistage-optimization/) | Shrink an image from about 900 MB to about 7 MB with a multi-stage build | Docker | 20 min |

All three labs were run end to end before they were published, and the expected output in each README comes from those runs.

## Tips

- Try each step yourself before you open the hints and answers.
- After a lab, explain out loud what broke, how you found it, and how you fixed it. That is the shape of a good troubleshooting answer.
- Clean up when you finish. Each README ends with the commands to do so.
