Departments of Finance blocklist crawler
=========

- The goal of this repository is to provide automatic crawler to
  download blocklists provided by European Departments of Finance using
  the best format possible.
- To run this project Docker is required. The output of the processed
  pdfs is csv and the output is persisted to **/opt/crawler/exports**
- The following countries are supported: Czech Republic, Slovak Republic
  and Bulgaria.


Environment variables for container
=========
- CZ_SOURCE, SK_SOURCE, BG_SOURCE: the pdf url with the variable part
  replaced by {}. Example:
  **https://www.mfcr.cz/assets/cs/media/Pdf_v{}.pdf**
- CHECK_PERIOD: the amount of minutes between each crawl
- BG_REFERENCE: the page where the Bulgarian pdf is located. It is
  needed to get the current id of the pdf.
- ERROR_API: monitoring api to which the errors should be sent.