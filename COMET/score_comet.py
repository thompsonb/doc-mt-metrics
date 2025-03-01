# Original Copyright (C) 2020 Unbabel
# Modifications Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.

import argparse
import json
from add_context import add_context
from comet import download_model, load_from_checkpoint


def main(args):
    model_name = "wmt21-comet-mqm" if args.use_ref else "wmt21-comet-qe-mqm"
    model_path = download_model(model_name)
    model = load_from_checkpoint(model_path)
    if args.doc:
        model.set_document_level()

    scores_path = args.dir + "scores/{}comet21{}_scores.json".format("doc" if args.context else "",
                                                                     "-qe" if not args.use_ref else "")

    scores = {}

    src = open(args.source, "r").read().splitlines()
    cand = open(args.hyp, "r").read().splitlines()
    if args.use_ref:
        ref = open(args.target, "r").read().splitlines()

    if args.doc:
        doc_lens = open(args.doc_lens, "r").read().splitlines()

        # add contexts to reference and source texts
        src = add_context(org_txt=src, context=src, docs=doc_lens, sep_token=model.encoder.tokenizer.sep_token)

        if args.use_ref:
            cand = add_context(org_txt=cand, context=ref, docs=doc_lens, sep_token=model.encoder.tokenizer.sep_token)
            ref = add_context(org_txt=ref, context=ref, docs=doc_lens, sep_token=model.encoder.tokenizer.sep_token)
        else:
            cand = add_context(org_txt=cand, context=cand, docs=doc_lens, sep_token=model.encoder.tokenizer.sep_token)

    if args.use_ref:
        data = [{"src": x, "mt": y, "ref": z} for x, y, z in zip(src, cand, ref)]
    else:
        data = [{"src": x, "mt": y} for x, y in zip(src, cand)]

    seg_score, sys_score = model.predict(data, batch_size=32, gpus=1)
    scores[args.level] = [float(sys_score) if not args.seg else [float(x) for x in seg_score]]

    with open(scores_path, 'w') as fp:
        json.dump(scores, fp)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Score COMET models.')
    parser.add_argument('--doc', action="store_true", help='document- or sentence-level comet')
    parser.add_argument('--dir', default="", type=str, help='directory where the scores will be saved')
    parser.add_argument('--source', required=True, type=str, help='the source text')
    parser.add_argument('--hyp', required=True, type=str, help='the translated text')
    parser.add_argument('--target', required=False, type=str, help='the target text')
    parser.add_argument('--doc_lens', required=False, type=str, help='the lengths of each document in the data')
    parser.add_argument('--use_ref', required=False, default=True,
                        help='whether evaluation is reference-based or reference-free')
    parser.add_argument('--level', required=False, default="sys", choices=["seg", "sys"],
                        help='whether segment-level or system-level scores will be computed')

    args = parser.parse_args()

    main(args)
