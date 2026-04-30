from minline import MinlineApp
from minline.session import SqliteSessionManager

app = MinlineApp(
    token="TOKEN",
    session_manager=SqliteSessionManager("sessions.db")
)

@app.route("/")
def main():
    return "AITU Gaming Bot Online"

if __name__ == "__main__":
    app.run()