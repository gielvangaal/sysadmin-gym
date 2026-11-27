#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
build=$(mktemp -d)
trap 'gpgconf --homedir "$build/gnupg" --kill gpg-agent 2>/dev/null || true; rm -rf -- "$build"' EXIT
mkdir -m 700 "$build/gnupg"
mkdir "$build"/{tmp,rpmdb,repo}
key='Sysadmin Gym Disposable Fixture <lab@gym.invalid>'
gpg --homedir "$build/gnupg" --batch --pinentry-mode loopback --passphrase '' \
    --quick-generate-key "$key" rsa2048 sign 0
gpg --homedir "$build/gnupg" --armor --export lab@gym.invalid > "$build/repo/KEY.asc"
rpmkeys --dbpath "$build/rpmdb" --import "$build/repo/KEY.asc"

for version in 1.0 2.0; do
    rpmbuild --define "_topdir $build" --define "_dbpath $build/rpmdb" \
        --define "_tmppath $build/tmp" --define "gym_version $version" -bb fixtures/gym-workload.spec
    package="$build/RPMS/noarch/gym-workload-$version-1.noarch.rpm"
    rpmsign --define "_gpg_name lab@gym.invalid" --define "_gpg_path $build/gnupg" \
        --define "_tmppath $build/tmp" --addsign "$package"
    rpmkeys --dbpath "$build/rpmdb" --checksig "$package"
    cp "$package" "$build/repo/"
done

createrepo_c --no-database --compress-type gz "$build/repo"
gpg --homedir "$build/gnupg" --armor --detach-sign \
    --output "$build/repo/repodata/repomd.xml.asc" "$build/repo/repodata/repomd.xml"
mkdir -p fixtures/rpm
cp "$build/repo/KEY.asc" "$build/repo/"*.rpm fixtures/rpm/
rm -rf -- fixtures/rpm/repodata
cp -a "$build/repo/repodata" fixtures/rpm/
