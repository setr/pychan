#!/usr/bin/env python
import click
import db_main as db

@click.group()
def cli():
    pass

@click.command()
@click.argument("boardname", required=True)
@click.argument("postids", nargs=-1, required=True)
def delete_post(boardname, postids):
    boardid = db.get_boardid(boardname)
    for pid in postids:
        real_pid = db_main._get_realpostid(boardid, pid)
        db_main.delete_post(real_pid, "", ismod=True)

@click.command()
@click.argument("board", required=True)
@click.argument("postids", nargs=-1, required=True, help="the post id for each thread")
def autosage(boardname, postids):
    boardid = db.get_boardid(boardname)
    for pid in postids:
        real_pid = db_main._get_realpostid(boardid, pid)
        db_main.mark_thread_autosage(real_pid)

if __name__ == '__main__':
    cli()


