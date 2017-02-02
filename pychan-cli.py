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
        real_pid = db._get_realpostid(boardid, pid)
        db.delete_post(real_pid, "", ismod=True)


@click.command()
@click.argument("board", required=True)
@click.argument("postids", nargs=-1, required=True)
def autosage(boardname, postids):
    boardid = db.get_boardid(boardname)
    for pid in postids:
        real_pid = db._get_realpostid(boardid, pid)
        db.mark_thread_autosage(real_pid)


@click.command()
@click.argument("boardname", required=True)
@click.argument("subtitle", required=True)
@click.argument("slogan", default="", required=False)
def new_board(boardname, subtitle, slogan):
    db.create_board(boardname, subtitle, slogan)


@click.command()
@click.argument("boardname", required=True)
@click.argument("postids", nargs=-1, required=True)
def mark_dirty(boardname, postids):
    boardid = db.get_boardid(boardname)
    for pid in postids:
        real_pid = db._get_realpostid(boardid, pid)
        db.mark_dirtyclean(real_pid, True)
    db.reparse_dirty_posts(boardname, boardid)


if __name__ == '__main__':
    cli.add_command(delete_post)
    cli.add_command(autosage)
    cli.add_command(new_board)
    cli.add_command(mark_dirty)
    cli()
