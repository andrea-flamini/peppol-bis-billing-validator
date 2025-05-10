#!/bin/bash

# Usage: ./compile-schematron.sh input.sch output.xslt

if [ "$#" -ne 2 ]; then
  echo "❗ Uso: $0 input.sch output.xslt"
  exit 1
fi

INPUT_SCH=$1
OUTPUT_XSLT=$2

SAXON_JAR="/home/pi/peppol-bis-billing-validator/saxon/saxon-he-12.6.jar"
XSL_DIR="/home/pi/peppol-bis-billing-validator/schematron"

echo "🔧 Compilazione schematron in corso..."
echo "Input: $INPUT_SCH"
echo "Output: $OUTPUT_XSLT"

# Passaggi: include → abstract_expand → svrl
java -jar "$SAXON_JAR" -s:"$INPUT_SCH" -xsl:"$XSL_DIR/iso_dsdl_include.xsl" -o:"$OUTPUT_XSLT.step1"
java -jar "$SAXON_JAR" -s:"$OUTPUT_XSLT.step1" -xsl:"$XSL_DIR/iso_abstract_expand.xsl" -o:"$OUTPUT_XSLT.step2"
java -jar "$SAXON_JAR" -s:"$OUTPUT_XSLT.step2" -xsl:"$XSL_DIR/iso_svrl_for_xslt2.xsl" -o:"$OUTPUT_XSLT"

# Pulizia file temporanei
rm "$OUTPUT_XSLT.step1" "$OUTPUT_XSLT.step2"

echo "✅ Compilazione completata: $OUTPUT_XSLT"

