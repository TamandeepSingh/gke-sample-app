# ============================================================
# app.py — Flask calculator web application
# ============================================================
# Flask is a lightweight Python web framework.
# It maps URL routes to Python functions and returns HTML responses.
#
# Why Flask for this demo?
#   - Minimal setup: no database, no ORM, no config files needed.
#   - Easy to containerise: one process, one port.
#   - Clear request/response cycle makes it easy to learn.

from flask import Flask, render_template, request

# Flask(__name__) creates the app.
# __name__ tells Flask where to look for templates and static files
# (relative to this file's location).
app = Flask(__name__)


# ---------------------------------------------------------------
# Route: GET /
# ---------------------------------------------------------------
# @app.route decorates a function to handle a specific URL path.
# When a browser visits "/", Flask calls index() and returns its result.
@app.route("/")
def index():
    # render_template loads app/templates/index.html and returns it as HTML.
    # No calculation on a plain GET — just show the empty form.
    return render_template("index.html", result=None, error=None)


# ---------------------------------------------------------------
# Route: POST /calculate
# ---------------------------------------------------------------
# HTML forms submit data via POST. The form in index.html posts here.
# request.form is a dict-like object containing the submitted fields.
@app.route("/calculate", methods=["POST"])
def calculate():
    try:
        # Convert form strings to floats so we can do arithmetic.
        # float() raises ValueError if the input isn't a valid number.
        a = float(request.form["a"])
        b = float(request.form["b"])
        op = request.form["op"]  # one of: add, subtract, multiply, divide

        if op == "add":
            result = a + b
            symbol = "+"
        elif op == "subtract":
            result = a - b
            symbol = "−"
        elif op == "multiply":
            result = a * b
            symbol = "×"
        elif op == "divide":
            if b == 0:
                # Division by zero is mathematically undefined.
                # Return an error message instead of crashing.
                return render_template("index.html", result=None, error="Cannot divide by zero")
            result = a / b
            symbol = "÷"
        else:
            return render_template("index.html", result=None, error="Unknown operation")

        # Format the result: show as int when there's no fractional part
        # (e.g. 6.0 → "6"), otherwise show up to 6 decimal places.
        result_str = int(result) if result == int(result) else round(result, 6)
        expression = f"{a} {symbol} {b} = {result_str}"

        return render_template("index.html", result=result_str, expression=expression, error=None)

    except ValueError:
        # Triggered if the user typed letters instead of numbers.
        return render_template("index.html", result=None, error="Please enter valid numbers")


# ---------------------------------------------------------------
# Health check endpoint
# ---------------------------------------------------------------
# Kubernetes liveness and readiness probes call this URL.
# It must return HTTP 200 quickly — no heavy logic here.
# The GCP load balancer also uses this to decide if a node is healthy.
@app.route("/healthz")
def healthz():
    return "ok", 200


# ---------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------
# This block only runs when you execute "python app.py" directly.
# When Docker/gunicorn runs the app, it imports the module instead,
# so this block is skipped (which is correct — gunicorn manages workers).
if __name__ == "__main__":
    # host="0.0.0.0" makes Flask listen on all network interfaces,
    # not just localhost. Required inside a container so traffic
    # from outside the container can reach the process.
    # port=8080 is the convention for non-root containerised apps
    # (ports below 1024 require root privileges).
    app.run(host="0.0.0.0", port=8080, debug=False)
