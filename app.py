#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Учебное веб-приложение "Заметки" на стандартной библиотеке Python.
# Запуск:  python3 app.py   ->  http://127.0.0.1:8000/

import html
import os
import sqlite3
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

HOST = "127.0.0.1"
PORT = 8000
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lab2.db")


def init_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, password TEXT, role TEXT)")
    conn.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, author TEXT, body TEXT)")
    conn.executemany("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", [
        ("admin", "S3cr3t_Admin_Pass!", "admin"),
        ("alice", "qwerty123", "user"),
        ("bob", "password", "user"),
    ])
    conn.executemany("INSERT INTO notes (author, body) VALUES (?, ?)", [
        ("alice", "Купить молоко и хлеб"),
        ("bob", "Не забыть про дедлайн по лабе"),
    ])
    conn.commit()
    conn.close()


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


PAGE = """<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8"><title>Заметки</title>
<style>body{{font-family:sans-serif;max-width:700px;margin:2rem auto;padding:0 1rem}}
nav a{{margin-right:.6rem}} input{{padding:.3rem}} div{{margin:.3rem 0}}</style></head><body>
<nav><a href="/">Главная</a><a href="/login">Вход</a><a href="/notes">Заметки</a><a href="/search">Поиск</a></nav>
<hr>{body}</body></html>"""


class Handler(BaseHTTPRequestHandler):

    def send_html(self, body, status=200):
        data = PAGE.format(body=body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def redirect(self, location):
        self.send_response(303)
        self.send_header("Location", location)
        self.end_headers()

    def form_data(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8")
        return {k: v[0] for k, v in urllib.parse.parse_qs(raw).items()}

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        if parsed.path == "/":
            self.page_home()
        elif parsed.path == "/login":
            self.page_login()
        elif parsed.path == "/notes":
            self.page_notes()
        elif parsed.path == "/search":
            self.page_search(params.get("q", [""])[0])
        else:
            self.send_html("<h1>404</h1>", 404)

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        form = self.form_data()
        if path == "/login":
            self.do_login(form.get("username", ""), form.get("password", ""))
        elif path == "/notes":
            self.do_add_note(form.get("author", "guest"), form.get("body", ""))
        else:
            self.send_html("<h1>404</h1>", 404)

    def page_home(self):
        self.send_html("<h1>Сайт заметок</h1><p>Учебное приложение.</p>")

    def page_login(self, message=""):
        self.send_html("""
        <h1>Вход</h1>{msg}
        <form method="POST" action="/login">
          <p>Логин: <input name="username"></p>
          <p>Пароль: <input name="password" type="text"></p>
          <button type="submit">Войти</button>
        </form>""".format(msg=message))

    def do_login(self, username, password):
        query = "SELECT username, role FROM users WHERE username = '%s' AND password = '%s'" % (username, password)
        conn = db()
        try:
            row = conn.execute(query).fetchone()
        except sqlite3.Error:
            row = None
        conn.close()
        if row:
            self.send_html("<h1>Вход выполнен</h1><p>Добро пожаловать, %s (роль: %s).</p>"
                           % (row["username"], row["role"]))
        else:
            self.page_login("<p>Неверный логин или пароль.</p>")

    def page_notes(self):
        conn = db()
        rows = conn.execute("SELECT author, body FROM notes ORDER BY id DESC").fetchall()
        conn.close()
        items = ""
        for r in rows:
            items += "<div><b>%s</b>: %s</div>" % (r["author"], r["body"])
        self.send_html("""
        <h1>Заметки</h1>{items}
        <h2>Добавить</h2>
        <form method="POST" action="/notes">
          <p>Автор: <input name="author" value="guest"></p>
          <p>Текст: <input name="body"></p>
          <button type="submit">Сохранить</button>
        </form>""".format(items=items))

    def do_add_note(self, author, body):
        conn = db()
        conn.execute("INSERT INTO notes (author, body) VALUES (?, ?)", (author, body))
        conn.commit()
        conn.close()
        self.redirect("/notes")

    def page_search(self, q):
        self.send_html("""
        <h1>Поиск</h1>
        <form method="GET" action="/search"><input name="q"><button>Искать</button></form>
        <p>Вы искали: %s</p>""" % q)


if __name__ == "__main__":
    init_db()
    print("Запущено: http://%s:%d/  (Ctrl+C для остановки)" % (HOST, PORT))
    try:
        HTTPServer((HOST, PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\nОстановлено.")
