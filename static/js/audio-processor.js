class AudioProcessor extends AudioWorkletProcessor {
    process(inputs, outputs, parameters) {
        const input = inputs[0];
        if (input && input.length > 0) {
            const channelData = input[0];
            if (channelData && channelData.length > 0) {
                this.port.postMessage(new Float32Array(channelData));
            }
        }
        return true;
    }
}

registerProcessor('audio-processor', AudioProcessor);
