
from flask import Flask, request, render_template_string, send_file
from lxml import etree
import subprocess
import tempfile
import os

app = Flask(__name__)

SAXON_JAR = "/home/pi/peppol-bis-billing-validator/saxon/saxon-he-12.6.jar"
RULESET_DIR = "/home/pi/peppol-bis-billing-validator/rulesets"
XSD_DIR = "/home/pi/peppol-bis-billing-validator/xsd/maindoc"

HTML_FORM = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>PEPPOL Validator</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <script>
    function disableForm() {
      const btn = document.getElementById("submitBtn");
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Validating...';
    }
  </script>
</head>
<body>
<div class="container mt-4">
  <h2 class="mb-4">🧾 PEPPOL XML Validator</h2>
  <form action="/validate" method="post" enctype="multipart/form-data" class="card p-4 shadow-sm" onsubmit="disableForm()">
    <div class="mb-3">
      <label for="xsd_schema" class="form-label">Select XSD schema:</label>
      <select name="xsd_schema" class="form-select" required>
        {% for key, filename in xsd_schemas.items() %}
          <option value="{{ filename }}">{{ key }}</option>
        {% endfor %}
      </select>
    </div>
    <div class="mb-3">
      <label for="ruleset" class="form-label">Select Schematron ruleset:</label>
      <select name="ruleset" class="form-select" required>
        {% for key, filename in rulesets.items() %}
          <option value="{{ key }}">{{ key }}</option>
        {% endfor %}
      </select>
    </div>
    <div class="mb-3">
      <label for="file" class="form-label">Upload XML file:</label>
      <input type="file" name="file" class="form-control" required>
    </div>
    <button id="submitBtn" type="submit" class="btn btn-primary">Validate</button>
  </form>

  {% if summary %}
    <h4 class="mt-5">Summary</h4>
    <table class="table table-bordered text-center">
      <thead class="table-light">
        <tr>
          <th>Validation type</th>
          <th>Validation artifact</th>
          <th>Warnings</th>
          <th>Errors</th>
        </tr>
      </thead>
      <tbody>
        {% for row in summary %}
        <tr class="{{ 'table-danger' if row.errors > 0 else 'table-success' }}">
          <td>{{ row.step }}</td>
          <td>{{ row.artifact }}</td>
          <td>{{ row.warnings }}</td>
          <td>{{ row.errors }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  {% endif %}

  {% if errori %}
    <div class="alert alert-danger mt-4">
      <h5>❌ Validation Details:</h5>
      <ul>
        {% for err in errori %}
          <li><strong>{{ err.msg }}</strong> <br><small>Location: {{ err.location }}</small></li>
        {% endfor %}
      </ul>
    </div>
  {% elif result %}
    <div class="alert alert-success mt-4">{{ result }}</div>
  {% endif %}

  {% if download_link %}
    <p class="mt-3"><a href="{{ download_link }}" class="btn btn-outline-secondary" download>📥 Download SVRL Report</a></p>
  {% endif %}
</div>
</body>
</html>
"""

def get_rulesets():
    return {os.path.splitext(f)[0]: f for f in os.listdir(RULESET_DIR) if f.endswith(".xslt")}

def get_xsd_schemas():
    return {os.path.splitext(f)[0]: f for f in os.listdir(XSD_DIR) if f.endswith(".xsd")}

def validate_with_xsd(xml_bytes, xsd_filename):
    xsd_path = os.path.join(XSD_DIR, xsd_filename)
    try:
        xml_doc = etree.fromstring(xml_bytes)
        with open(xsd_path, 'rb') as f:
            xsd_doc = etree.parse(f)
        xmlschema = etree.XMLSchema(xsd_doc)
        xmlschema.assertValid(xml_doc)
        return [], {"step": "XML Schema", "artifact": xsd_filename, "warnings": 0, "errors": 0}
    except etree.DocumentInvalid as e:
        return [{"msg": str(e), "location": "XSD validation"}], {"step": "XML Schema", "artifact": xsd_filename, "warnings": 0, "errors": 1}
    except Exception as e:
        return [{"msg": f"XSD validation error: {str(e)}", "location": "XSD validation"}], {"step": "XML Schema", "artifact": xsd_filename, "warnings": 0, "errors": 1}

def validate_with_saxon(xml_bytes, ruleset):
    xslt_file = os.path.join(RULESET_DIR, f"{ruleset}.xslt")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xml") as tmp:
        tmp.write(xml_bytes)
        tmp_path = tmp.name
    output_path = f"/tmp/validated_{ruleset}.svrl.xml"

    try:
        cmd = ["java", "-jar", SAXON_JAR, "-s:" + tmp_path, "-xsl:" + xslt_file, "-o:" + output_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return [{"msg": result.stderr, "location": "Schematron"}], None, {"step": "Schematron (XSLT2)", "artifact": xslt_file, "warnings": 0, "errors": 1}

        tree = etree.parse(output_path)
        failed = tree.xpath('//svrl:failed-assert', namespaces={'svrl': 'http://purl.oclc.org/dsdl/svrl'})
        warnings = [f for f in failed if 'flag="warning"' in etree.tostring(f).decode()]
        errors = len(failed) - len(warnings)

        details = []
        for f in failed:
            msg = f.findtext('svrl:text', namespaces={'svrl': 'http://purl.oclc.org/dsdl/svrl'})
            loc = f.get('location', '')
            details.append({"msg": msg, "location": loc})

        return details, output_path, {"step": "Schematron (XSLT2)", "artifact": os.path.basename(xslt_file), "warnings": len(warnings), "errors": errors}
    finally:
        os.remove(tmp_path)

@app.route("/", methods=["GET"])
def index():
    return render_template_string(HTML_FORM, rulesets=get_rulesets(), xsd_schemas=get_xsd_schemas())

@app.route("/validate", methods=["POST"])
def validate_route():
    if 'file' not in request.files:
        return render_template_string(HTML_FORM, rulesets=get_rulesets(), xsd_schemas=get_xsd_schemas(),
                                      errori=[{"msg": "No XML file uploaded", "location": "form"}])

    xml_file = request.files['file']
    ruleset = request.form.get('ruleset')
    xsd_schema = request.form.get('xsd_schema')
    xml_bytes = xml_file.read()

    summary = []

    # XSD validation
    xsd_errors, xsd_result = validate_with_xsd(xml_bytes, xsd_schema)
    summary.append(xsd_result)
    if xsd_errors:
        return render_template_string(HTML_FORM, rulesets=get_rulesets(), xsd_schemas=get_xsd_schemas(),
                                      errori=xsd_errors, summary=summary)

    # Schematron validation
    schematron_errors, svrl_path, schematron_result = validate_with_saxon(xml_bytes, ruleset)
    summary.append(schematron_result)
    if schematron_errors:
        return render_template_string(HTML_FORM, rulesets=get_rulesets(), xsd_schemas=get_xsd_schemas(),
                                      errori=schematron_errors, summary=summary)

    return render_template_string(HTML_FORM, rulesets=get_rulesets(), xsd_schemas=get_xsd_schemas(),
                                  result="✅ The document is valid according to both XSD and Schematron rules.",
                                  download_link="/download/" + os.path.basename(svrl_path),
                                  summary=summary)

@app.route("/download/<filename>")
def download_svrl(filename):
    return send_file("/tmp/" + filename, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
