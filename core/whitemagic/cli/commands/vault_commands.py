# mypy: disable-error-code=no-untyped-def
"""Vault CLI Commands
Encrypted local secret storage.
"""

import click


@click.group(name="vault")
def vault_group() -> None:
    """Encrypted local secret storage."""


@vault_group.command(name="init")
@click.option("--passphrase", "-p", prompt=True, hide_input=True, confirmation_prompt=True, help="Passphrase for vault encryption")
def vault_init(passphrase: str) -> None:
    """Initialize the encrypted vault."""
    from whitemagic.config.paths import WM_ROOT
    from whitemagic.security.vault import Vault
    Vault(passphrase=passphrase)
    click.echo(f"Vault initialized at {WM_ROOT / 'vault' / 'secrets.db'}")
    click.echo("Your secrets are encrypted with AES-256.")


@vault_group.command(name="set")
@click.argument("name")
@click.argument("value", required=False)
@click.option("--passphrase", "-p", envvar="WM_VAULT_PASSPHRASE", default=None, help="Vault passphrase")
def vault_set(name: str, value: str | None, passphrase: str | None) -> None:
    """Store an encrypted secret. VALUE can be omitted to prompt securely."""
    from whitemagic.security.vault import get_vault
    if value is None:
        value = click.prompt(f"Value for {name}", hide_input=True)
    vault = get_vault(passphrase=passphrase)
    vault.set(name, value)
    click.echo(f"Stored: {name}")


@vault_group.command(name="get")
@click.argument("name")
@click.option("--passphrase", "-p", envvar="WM_VAULT_PASSPHRASE", default=None, help="Vault passphrase")
def vault_get(name: str, passphrase: str | None) -> None:
    """Retrieve a decrypted secret."""
    from whitemagic.security.vault import get_vault
    vault = get_vault(passphrase=passphrase)
    val = vault.get(name)
    if val is None:
        click.echo(f"Not found: {name}", err=True)
        raise SystemExit(1)
    click.echo(val)


@vault_group.command(name="list")
@click.option("--passphrase", "-p", envvar="WM_VAULT_PASSPHRASE", default=None, help="Vault passphrase")
def vault_list(passphrase: str | None) -> None:
    """List stored secret names (values are never shown)."""
    from whitemagic.security.vault import get_vault
    vault = get_vault(passphrase=passphrase)
    names = vault.list()
    if not names:
        click.echo("Vault is empty.")
        return
    for n in names:
        click.echo(f"  {n}")


@vault_group.command(name="delete")
@click.argument("name")
@click.option("--passphrase", "-p", envvar="WM_VAULT_PASSPHRASE", default=None, help="Vault passphrase")
def vault_delete(name: str, passphrase: str | None) -> None:
    """Delete a secret from the vault."""
    from whitemagic.security.vault import get_vault
    vault = get_vault(passphrase=passphrase)
    if vault.delete(name):
        click.echo(f"Deleted: {name}")
    else:
        click.echo(f"Not found: {name}", err=True)


@vault_group.command(name="rekey")
@click.option("--new-passphrase", prompt=True, hide_input=True, confirmation_prompt=True, help="New passphrase")
@click.option("--passphrase", "-p", envvar="WM_VAULT_PASSPHRASE", default=None, help="Current vault passphrase")
def vault_rekey(new_passphrase: str, passphrase: str | None) -> None:
    """Re-encrypt all secrets with a new passphrase."""
    from whitemagic.security.vault import get_vault
    vault = get_vault(passphrase=passphrase)
    vault.rekey(new_passphrase)
    click.echo("Vault re-keyed successfully.")
