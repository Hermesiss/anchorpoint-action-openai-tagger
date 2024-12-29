import tiktoken


def count_tokens(in_prompt, model="gpt-4o-mini"):
    encoding = tiktoken.encoding_for_model(model)
    tokens = encoding.encode(in_prompt)
    return len(tokens)
