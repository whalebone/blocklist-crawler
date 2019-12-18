import csv
from urlextract import URLExtract


def format_url(url: str) -> str:
    if url.endswith("/"):
        url = url[:-1]
    return url.split("//")[-1]


def compare_results(src, domains):
    domains = set(domains)
    out_csv = set()
    with open("mf{}.csv".format(src), "r") as out:
        for row in out:
            out_csv.add(row.replace("\n", ""))
    if out_csv == domains:
        print("Source {} ok".format(src))
    else:
        print("Source {} failed".format(src))
        print("Parsed: {}".format(len(out_csv)))
        print("From pdf: {}".format(len(domains)))


def parse_pdf(source):
    index = {"cz": 0, "sk": 1, "bg": 1}
    extractor = URLExtract()
    urls = []
    with open("{}.csv".format(source), "r", encoding="utf-8") as file:
        reader = csv.reader(file)
        for line in reader:
            for url in extractor.gen_urls(line[index[source]]):
                urls.append(url)
    return [format_url(url) for url in urls]


for source in ["cz", "sk", "bg"]:
    compare_results(source, parse_pdf(source))
