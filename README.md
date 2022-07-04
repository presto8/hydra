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
- Automatically verifies backup data on a schedule
- Reports if backup is out of date or insufficient
- All configuration and settings stored in git for revision control and
  disaster recovery
- Ability to create a USB recovery drive with everything needed to do a "cold
  restore"
- Ability to backup essential information to paper copy
- Easy migration in or out: backup data is managed by the underlying backup
  programs, so you are able to start or stop using hydra any time you want.

## Philosophies

- Use diversity of implementation. Don't rely on any single entity.
  - For the program used to back up the data, use multiple different backup
    programs.
  - For the providers used to store the data, use multiple different storage
    providers.

## Tech Stack

Hydra doesn't reinvent the wheel. It stands on the shoulders of giants:

- Backup programs: restic, hashbackup, duplicacy, kopia, ...
- File transfer (for backup to peers): syncthing
- Storage of secrets: password-store (pass), gpg
