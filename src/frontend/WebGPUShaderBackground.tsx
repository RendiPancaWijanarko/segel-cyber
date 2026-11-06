import React, { useEffect, useRef } from 'react';
import tgpu, { d } from 'typegpu';

// TypeGPU Data Schema for Uniforms
const ShaderUniforms = d.struct({
  resolution: d.vec2f,
  time: d.f32,
  pad: d.f32,
});

const WGSL_SHADER = /* wgsl */ `
struct Uniforms {
  resolution: vec2f,
  time: f32,
  pad: f32,
};

@group(0) @binding(0) var<uniform> u: Uniforms;

struct VertexOutput {
  @builtin(position) position: vec4f,
  @location(0) uv: vec2f,
};

@vertex
fn vs_main(@builtin(vertex_index) vertexIndex: u32) -> VertexOutput {
  // Full-screen triangle covering [-1, 3] in clip space
  var pos = array<vec2f, 3>(
    vec2f(-1.0, -1.0),
    vec2f( 3.0, -1.0),
    vec2f(-1.0,  3.0)
  );
  var out: VertexOutput;
  let p = pos[vertexIndex];
  out.position = vec4f(p, 0.0, 1.0);
  out.uv = (p + vec2f(1.0, 1.0)) * 0.5;
  out.uv.y = 1.0 - out.uv.y; // Screen coordinates: top-left (0,0) to bottom-right (1,1)
  return out;
}

@fragment
fn fs_main(in: VertexOutput) -> @location(0) vec4f {
  let uv = in.uv;
  let aspect = vec2f(u.resolution.x / u.resolution.y, 1.0);
  
  // Origin: Upper-left corner
  let origin = vec2f(-0.06, -0.06);
  let p = (uv - origin) * aspect;
  let r = length(p);
  let theta = atan2(p.y, p.x);

  // Smooth, subtle fluid silk fold distortion
  let fold = sin(r * 9.0 - theta * 3.2 + u.time * 0.22) * 0.075 
           + cos(r * 18.0 + theta * 4.8) * 0.032;
  let warpedTheta = theta + fold;

  // Multi-frequency angular ray generation
  var rays = 0.0;
  rays += (sin(warpedTheta * 14.0) * 0.5 + 0.5) * 0.44;
  rays += (sin(warpedTheta * 30.0 + 1.2) * 0.5 + 0.5) * 0.28;
  rays += (sin(warpedTheta * 62.0 + 2.5) * 0.5 + 0.5) * 0.18;
  rays += (sin(warpedTheta * 110.0 + 4.0) * 0.5 + 0.5) * 0.10;
  rays = pow(rays, 1.8) * 1.6;

  // Soft caustics crest
  var crest = sin(r * 7.5 - warpedTheta * 6.5 + fold * 4.0);
  crest = smoothstep(-0.35, 0.65, crest);

  // Radial and angular envelopes
  let radialFalloff = smoothstep(0.04, 0.38, r) * smoothstep(1.7, 0.52, r);
  let angularMask = smoothstep(0.02, 0.42, theta) * smoothstep(1.38, 0.88, theta);

  let rayIntensity = rays * crest * radialFalloff * angularMask;
  let ambientSheen = crest * radialFalloff * angularMask * 0.26;

  // --- Light Mode Triadic Color Composition ---
  let c_canvas     = vec3f(0.948, 0.970, 0.942); // Clean military white-sage (#F2F7F0)
  let c_sage_soft  = vec3f(0.720, 0.825, 0.680); // TNI AD Sage Green (60%)
  let c_sage_deep  = vec3f(0.480, 0.620, 0.420); // Tactical Midtone
  let c_sand_gold  = vec3f(0.820, 0.740, 0.600); // Warm Sand / Bronze (30%)
  let c_mint_flare = vec3f(0.920, 0.990, 0.950); // Luminous Mint Glow (10%)
  let c_lavender   = vec3f(0.850, 0.810, 0.930); // Triadic Iridescent Accent

  // 1. Blend ambient sage over the bright canvas base
  var color = mix(c_canvas, c_sage_soft, clamp(ambientSheen * 1.8, 0.0, 0.85));

  // 2. Add tactical sand/bronze warmth into the flowing folds
  color = mix(color, c_sand_gold, clamp(rayIntensity * 1.2, 0.0, 0.75));

  // 3. Modulate deeper sage ripples for depth
  let rippleShadow = pow(clamp(rayIntensity * (1.0 - crest * 0.5), 0.0, 1.0), 2.2);
  color = mix(color, c_sage_deep, rippleShadow * 0.35);

  // 4. Highlight crests with luminous mint and iridescent violet
  let specularPeak = pow(clamp(rayIntensity * crest, 0.0, 1.0), 3.0);
  let highlight = mix(c_mint_flare, c_lavender, sin(u.time * 0.5 + r * 4.0) * 0.5 + 0.5);
  color = mix(color, highlight, specularPeak * 0.65);

  return vec4f(color, 1.0);
}
`;

const GLSL_VS = `
attribute vec2 position;
void main() {
  gl_Position = vec4(position, 0.0, 1.0);
}
`;

const GLSL_FS = `
precision highp float;
uniform vec2 u_resolution;
uniform float u_time;

void main() {
  vec2 uv = gl_FragCoord.xy / u_resolution;
  uv.y = 1.0 - uv.y;
  vec2 aspect = vec2(u_resolution.x / u_resolution.y, 1.0);
  
  vec2 origin = vec2(-0.06, -0.06);
  vec2 p = (uv - origin) * aspect;
  float r = length(p);
  float theta = atan(p.y, p.x);

  float fold = sin(r * 9.0 - theta * 3.2 + u_time * 0.22) * 0.075 
             + cos(r * 18.0 + theta * 4.8) * 0.032;
  float warpedTheta = theta + fold;

  float rays = 0.0;
  rays += (sin(warpedTheta * 14.0) * 0.5 + 0.5) * 0.44;
  rays += (sin(warpedTheta * 30.0 + 1.2) * 0.5 + 0.5) * 0.28;
  rays += (sin(warpedTheta * 62.0 + 2.5) * 0.5 + 0.5) * 0.18;
  rays += (sin(warpedTheta * 110.0 + 4.0) * 0.5 + 0.5) * 0.10;
  rays = pow(rays, 1.8) * 1.6;

  float crest = sin(r * 7.5 - warpedTheta * 6.5 + fold * 4.0);
  crest = smoothstep(-0.35, 0.65, crest);

  float radialFalloff = smoothstep(0.04, 0.38, r) * smoothstep(1.7, 0.52, r);
  float angularMask = smoothstep(0.02, 0.42, theta) * smoothstep(1.38, 0.88, theta);

  float rayIntensity = rays * crest * radialFalloff * angularMask;
  float ambientSheen = crest * radialFalloff * angularMask * 0.26;

  vec3 c_canvas     = vec3(0.948, 0.970, 0.942);
  vec3 c_sage_soft  = vec3(0.720, 0.825, 0.680);
  vec3 c_sage_deep  = vec3(0.480, 0.620, 0.420);
  vec3 c_sand_gold  = vec3(0.820, 0.740, 0.600);
  vec3 c_mint_flare = vec3(0.920, 0.990, 0.950);
  vec3 c_lavender   = vec3(0.850, 0.810, 0.930);

  vec3 color = mix(c_canvas, c_sage_soft, clamp(ambientSheen * 1.8, 0.0, 0.85));
  color = mix(color, c_sand_gold, clamp(rayIntensity * 1.2, 0.0, 0.75));

  float rippleShadow = pow(clamp(rayIntensity * (1.0 - crest * 0.5), 0.0, 1.0), 2.2);
  color = mix(color, c_sage_deep, rippleShadow * 0.35);

  float specularPeak = pow(clamp(rayIntensity * crest, 0.0, 1.0), 3.0);
  vec3 highlight = mix(c_mint_flare, c_lavender, sin(u_time * 0.5 + r * 4.0) * 0.5 + 0.5);
  color = mix(color, highlight, specularPeak * 0.65);

  gl_FragColor = vec4(color, 1.0);
}
`;

export const WebGPUShaderBackground: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    let animationFrameId: number;
    let isDisposed = false;
    let resizeObserver: ResizeObserver | null = null;

    // WebGL Fallback implementation
    const initWebGLFallback = () => {
      const gl = (canvas.getContext('webgl2') || canvas.getContext('webgl')) as WebGLRenderingContext | null;
      if (!gl) return;

      const compileShader = (type: number, src: string) => {
        const s = gl.createShader(type);
        if (!s) return null;
        gl.shaderSource(s, src);
        gl.compileShader(s);
        return s;
      };

      const vs = compileShader(gl.VERTEX_SHADER, GLSL_VS);
      const fs = compileShader(gl.FRAGMENT_SHADER, GLSL_FS);
      if (!vs || !fs) return;

      const program = gl.createProgram();
      if (!program) return;
      gl.attachShader(program, vs);
      gl.attachShader(program, fs);
      gl.linkProgram(program);
      gl.useProgram(program);

      const buffer = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
      gl.bufferData(
        gl.ARRAY_BUFFER,
        new Float32Array([-1, -1, 3, -1, -1, 3]),
        gl.STATIC_DRAW
      );

      const posAttrib = gl.getAttribLocation(program, 'position');
      gl.enableVertexAttribArray(posAttrib);
      gl.vertexAttribPointer(posAttrib, 2, gl.FLOAT, false, 0, 0);

      const resLoc = gl.getUniformLocation(program, 'u_resolution');
      const timeLoc = gl.getUniformLocation(program, 'u_time');

      const handleResize = () => {
        const dpr = Math.min(window.devicePixelRatio || 1, 2);
        const width = Math.floor(canvas.clientWidth * dpr);
        const height = Math.floor(canvas.clientHeight * dpr);
        if (canvas.width !== width || canvas.height !== height) {
          canvas.width = width;
          canvas.height = height;
        }
        gl.viewport(0, 0, width, height);
      };

      resizeObserver = new ResizeObserver(handleResize);
      resizeObserver.observe(canvas);
      handleResize();

      const startTime = performance.now();
      const render = (now: number) => {
        if (isDisposed) return;
        const time = (now - startTime) * 0.001;
        gl.uniform2f(resLoc, canvas.width, canvas.height);
        gl.uniform1f(timeLoc, time);
        gl.drawArrays(gl.TRIANGLES, 0, 3);
        animationFrameId = requestAnimationFrame(render);
      };

      animationFrameId = requestAnimationFrame(render);
    };

    // Primary WebGPU + TypeGPU Pipeline
    const initWebGPU = async () => {
      // Check if WebGPU is available in browser
      if (!navigator.gpu) {
        initWebGLFallback();
        return;
      }

      try {
        // Initialize TypeGPU root
        const root = await tgpu.init();
        if (isDisposed) {
          root.destroy();
          return;
        }

        const device = root.device;
        const context = canvas.getContext('webgpu') as GPUCanvasContext | null;
        if (!context) {
          initWebGLFallback();
          return;
        }

        const format = navigator.gpu.getPreferredCanvasFormat();
        context.configure({
          device,
          format,
          alphaMode: 'premultiplied',
        });

        // Create shader module with the anisotropic ray shader
        const shaderModule = device.createShaderModule({
          label: 'Anisotropic Caustic Rays WGSL',
          code: WGSL_SHADER,
        });

        // 16-byte uniform buffer (2 floats resolution + 1 float time + 1 float padding)
        const uniformBuffer = device.createBuffer({
          label: 'ShaderUniformsBuffer',
          size: 16,
          usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST,
        });

        // Pipeline layout
        const bindGroupLayout = device.createBindGroupLayout({
          label: 'ShaderBindGroupLayout',
          entries: [
            {
              binding: 0,
              visibility: GPUShaderStage.FRAGMENT | GPUShaderStage.VERTEX,
              buffer: { type: 'uniform' },
            },
          ],
        });

        const bindGroup = device.createBindGroup({
          label: 'ShaderBindGroup',
          layout: bindGroupLayout,
          entries: [
            {
              binding: 0,
              resource: { buffer: uniformBuffer },
            },
          ],
        });

        const pipelineLayout = device.createPipelineLayout({
          label: 'ShaderPipelineLayout',
          bindGroupLayouts: [bindGroupLayout],
        });

        const pipeline = device.createRenderPipeline({
          label: 'AnisotropicRaysRenderPipeline',
          layout: pipelineLayout,
          vertex: {
            module: shaderModule,
            entryPoint: 'vs_main',
          },
          fragment: {
            module: shaderModule,
            entryPoint: 'fs_main',
            targets: [{ format }],
          },
          primitive: {
            topology: 'triangle-list',
          },
        });

        const uniformData = new Float32Array(4);

        const handleResize = () => {
          const dpr = Math.min(window.devicePixelRatio || 1, 2);
          const width = Math.max(1, Math.floor(canvas.clientWidth * dpr));
          const height = Math.max(1, Math.floor(canvas.clientHeight * dpr));
          if (canvas.width !== width || canvas.height !== height) {
            canvas.width = width;
            canvas.height = height;
          }
        };

        resizeObserver = new ResizeObserver(handleResize);
        resizeObserver.observe(canvas);
        handleResize();

        const startTime = performance.now();

        const render = (now: number) => {
          if (isDisposed) return;

          const time = (now - startTime) * 0.001;
          uniformData[0] = canvas.width;
          uniformData[1] = canvas.height;
          uniformData[2] = time;
          uniformData[3] = 0; // padding

          device.queue.writeBuffer(uniformBuffer, 0, uniformData.buffer);

          const commandEncoder = device.createCommandEncoder();
          const textureView = context.getCurrentTexture().createView();

          const renderPass = commandEncoder.beginRenderPass({
            colorAttachments: [
              {
                view: textureView,
                clearValue: { r: 0.948, g: 0.970, b: 0.942, a: 1.0 },
                loadOp: 'clear',
                storeOp: 'store',
              },
            ],
          });

          renderPass.setPipeline(pipeline);
          renderPass.setBindGroup(0, bindGroup);
          renderPass.draw(3, 1, 0, 0);
          renderPass.end();

          device.queue.submit([commandEncoder.finish()]);

          animationFrameId = requestAnimationFrame(render);
        };

        animationFrameId = requestAnimationFrame(render);
      } catch (err) {
        console.warn('WebGPU init failed, falling back to WebGL:', err);
        initWebGLFallback();
      }
    };

    initWebGPU();

    return () => {
      isDisposed = true;
      if (animationFrameId) cancelAnimationFrame(animationFrameId);
      if (resizeObserver) resizeObserver.disconnect();
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 w-full h-full pointer-events-none z-0"
      style={{
        position: 'fixed',
        inset: 0,
        width: '100vw',
        height: '100vh',
        zIndex: 0,
        pointerEvents: 'none',
      }}
    />
  );
};

