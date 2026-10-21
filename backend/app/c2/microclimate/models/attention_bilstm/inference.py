"""Register the attention model and reuse frozen inference/scaler validation."""
from . import model
from ..lstm.inference import infer, main


if __name__ == "__main__":
    main()
