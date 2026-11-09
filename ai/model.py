import json
from pathlib import Path

import torch
from torch import nn
from torch.nn import functional as F

VOCAB_SIZE = 260  # 256 UTF-8 byte values + PAD/BOS/EOS/UNK


class CausalSelfAttention(nn.Module):
    def __init__(self, width: int, heads: int):
        super().__init__()
        if width % heads:
            raise ValueError("width must be divisible by heads")
        self.heads = heads
        self.head_dim = width // heads
        self.qkv = nn.Linear(width, width * 3, bias=False)
        self.proj = nn.Linear(width, width, bias=False)

    def forward(self, x):
        batch, length, width = x.shape
        q, k, v = self.qkv(x).chunk(3, dim=-1)
        shape = (batch, length, self.heads, self.head_dim)
        q = q.view(shape).transpose(1, 2)
        k = k.view(shape).transpose(1, 2)
        v = v.view(shape).transpose(1, 2)
        out = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        out = out.transpose(1, 2).contiguous().view(batch, length, width)
        return self.proj(out)


class Block(nn.Module):
    def __init__(self, width: int, heads: int):
        super().__init__()
        self.ln1 = nn.LayerNorm(width)
        self.attn = CausalSelfAttention(width, heads)
        self.ln2 = nn.LayerNorm(width)
        self.mlp = nn.Sequential(
            nn.Linear(width, width * 4),
            nn.GELU(),
            nn.Linear(width * 4, width),
        )

    def forward(self, x):
        x = x + self.attn(self.ln1(x))
        return x + self.mlp(self.ln2(x))


class NexusGPT(nn.Module):
    def __init__(self, config: dict):
        super().__init__()
        width = int(config["width"])
        self.block_size = int(config["block_size"])
        self.token_embedding = nn.Embedding(VOCAB_SIZE, width)
        self.position_embedding = nn.Embedding(self.block_size, width)
        self.blocks = nn.Sequential(*[
            Block(width, int(config["heads"])) for _ in range(int(config["layers"]))
        ])
        self.final_norm = nn.LayerNorm(width)
        self.lm_head = nn.Linear(width, VOCAB_SIZE, bias=False)
        self.lm_head.weight = self.token_embedding.weight

    def forward(self, tokens):
        _, length = tokens.shape
        if length > self.block_size:
            tokens = tokens[:, -self.block_size:]
            length = tokens.shape[1]
        positions = torch.arange(length, device=tokens.device)
        x = self.token_embedding(tokens) + self.position_embedding(positions)[None, :, :]
        x = self.blocks(x)
        return self.lm_head(self.final_norm(x))


def encode(text: str):
    return [1] + [b + 4 for b in text.encode("utf-8")] + [2]


def decode(tokens):
    data = bytes(int(t) - 4 for t in tokens if 4 <= int(t) <= 259)
    return data.decode("utf-8", errors="replace")


def load_config(folder):
    return json.loads((Path(folder) / "config.json").read_text(encoding="utf-8"))
