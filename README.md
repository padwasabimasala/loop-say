A simple util to create speech to text loops for Bible memorization
but works with any input text file

## Usage

```
./bin/gen-audio some-text-file
```

## Secrets

The YouTube OAuth client and token JSON files are encrypted in place with SOPS
and a passphrase-protected age key.

```sh
make setup-secrets # first time only; creates the encrypted age key and SOPS config
make encrypt       # encrypt both JSON files in place
make decrypt       # decrypt both JSON files; prompts for the passphrase once
```

After encrypting, stage the encrypted files and key configuration explicitly:

```sh
git add -f .youtube-oauth-client.json .youtube-upload-token.json .sops-age-key.age .sops.yaml
```

## Options

Options are passed as envvars


WPM: how many word perminute for speech to text
REPEAT: how many times to repeat the text
FADE: how long to fade in and out of speech
BG: background track
VOICE: speech to text voice to use
SPACINGMS: space between repeats in milliseconds
ARTIST: Album artist info tag for output MP4
ALBUM: Album title info tag for output mp4
ARTWORK: Path to album artwork JPG for output mp4

