"""Frozen GRU inference using the existing scaler and inference contract."""
from . import model  # Register c2>MaskedGRU before loading.
from ..lstm.inference import infer, main


if __name__ == "__main__":
    main()
