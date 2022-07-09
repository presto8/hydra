# Hydra

<img src="assets/hydra.png" alt="A multi-headed hydra" align="right" style="width: 200px;" /></a>

Hydra is a meta backup program that manages other backup programs to ensure
data is backed up safely to multiple destinations.

The [Lernaean Hydra](https://en.wikipedia.org/wiki/Lernaean_Hydra) was a
serpent with many heads: for each head chopped off, the hydra would regrow two
heads, making it very difficult to kill. Similarly, Hydra (this program) has
many heads as well: it will keep your data safe by storing it in multiple
locations and also by using multiple different backup methods. Stanford's
[LOCKSS initiative](https://www.lockss.org/), intended for libraries, has a
similar philosophy: Lots of Copies Keeps Stuff Safe.

For example, if you want to backup your data to Dropbox and S3 using Restic and
Hashbackup, Hydra will take care of managing those other programs to ensure
that everything is backed up independently.

## Features

- Runs backups on a user-defined schedule
- Manages multiple backup programs (restic, hashbackup, ...)
- Manages multiple backup destinations (dropbox, s3, ...)
- Enables the highest available encryption level of the underlying backup
  program
- Configures underlying backup programs with the most conservative
  configuration settings, such as backing everything up by default.
- Automatically verifies backup data on a schedule, by restoring the data and
  verifying it.
- Reports if backup is out of date or insufficient
- All configuration and settings stored in git for revision control and
  disaster recovery
- Ability to create a USB recovery drive with everything needed to do a "cold
  restore"
- Ability to backup essential information to paper copy
- Easy migration in or out: backup data is managed by the underlying backup
  programs, so you are able to start or stop using hydra any time you want.
- Full logging for easier audit and troubleshooting

## Philosophies

- Use diversity of implementation. Don't rely on any single entity.
  - For the program used to backup the data, use multiple different backup
    programs.
  - For the providers used to store the data, use multiple different storage
    providers.

- Trust but verify.
  - Don't rely on built-in verification of a backup program. Independently
    verify data redundancy.

- Always use encryption.
  - Configure underlying backup programs with encryption.
  - Don't support backup programs that don't offer encryption.
  - Store secrets in pass/gpg.

- Store everything under revision control (git).


## User interface

- hydra init
- hydra backup
  - runs backup according to defined backup schedule
  - if backup is up-to-date, it will exit quickly
  - use --now flag to force a backup
- hydra doctor
  - runs a health check on the Hydra instance and reports any issues
- hydra verify
  - runs verify according to defined backup schedule
- hydra mount
- hydra restore
- hydra find


## Tech Stack

Hydra doesn't reinvent the wheel. It stands on the shoulders of giants:

- Backup programs: restic, hashbackup, duplicacy, kopia, ...
- Storage of configuration settings: git
- Storage of secrets: password-store (pass), gpg
- File transfer (for backup to peers): syncthing, minio, ...
