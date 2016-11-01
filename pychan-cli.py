#!/usr/bin/env python
import click
import db_main as db

@click.command()
@click.argument("postids", nargs=-1, required=True)
def delete_post(postids):
    for pid in postids:
        db_main.delete_post(pid, "", ismod=True)

if __name__ == '__main__':
    delete_post()


