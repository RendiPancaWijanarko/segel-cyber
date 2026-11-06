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
  let p = (uv - vec2f(-0.05, -0.05)) * aspect;
  let r = length(p);
  let theta = atan2(p.y, p.x);

  // Transverse Fabric Ripple (Warping)
  let fold = sin(r * 10.0 - theta * 3.5 + u.time * 0.25) * 0.08 
           + cos(r * 20.0 + theta * 5.0) * 0.035;
  let warpedTheta = theta + fold;

  // Ray Noise (Multi-Octave 1D Wave Accumulation)
  var rays = 0.0;
  rays += (sin(warpedTheta * 16.0) * 0.5 + 0.5) * 0.45;
  rays += (sin(warpedTheta * 34.0 + 1.2) * 0.5 + 0.5) * 0.28;
  rays += (sin(warpedTheta * 68.0 + 2.5) * 0.5 + 0.5) * 0.17;
  rays += (sin(warpedTheta * 128.0 + 4.1) * 0.5 + 0.5) * 0.10;
  rays = pow(rays, 2.4) * 2.2;

  // Modulating Wave Crests
  var crest = sin(r * 8.5 - warpedTheta * 7.0 + fold * 4.5);
  crest = smoothstep(-0.25, 0.75, crest);

  // Radial Windowing & Angular Mask
  let radialFalloff = smoothstep(0.08, 0.42, r) * smoothstep(1.65, 0.55, r);
  let angularMask = smoothstep(0.05, 0.45, theta) * smoothstep(1.35, 0.85, theta);
  let intensity = rays * crest * radialFalloff * angularMask;
  let ambient = crest * radialFalloff * angularMask * 0.22;

  // Triadic Military Color Palette (60% TNI AD Green, 30% Tactical Bronze, 10% Neon Accent Flares)
  let c_base    = vec3f(0.06, 0.11, 0.05); // Deep ambient olive (#12210F)
  let c_green   = vec3f(0.20, 0.33, 0.16); // TNI AD Army Green (60% - #335229)
  let c_bronze  = vec3f(0.44, 0.28, 0.10); // Tactical Bronze (30% - #70471A)
  let c_neon    = vec3f(0.60, 0.30, 1.00); // Electric Violet Accent (10% - #8C40FF)

  // Smooth triadic blending based on ray dynamics
  var col = mix(c_base, c_green, clamp(ambient * 2.5, 0.0, 1.0));
  col = mix(col, c_bronze, clamp(intensity * 1.4, 0.0, 1.0));

  // Accent highlight only at the highest specular peaks
  let specularPeak = pow(clamp(intensity * crest, 0.0, 1.0), 3.5);
  col = mix(col, c_neon, specularPeak * 0.85);

  return vec4f(col, 1.0);
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
  vec2 p = (uv - vec2(-0.05, -0.05)) * aspect;
  float r = length(p);
  float theta = atan(p.y, p.x);

  float fold = sin(r * 10.0 - theta * 3.5 + u_time * 0.25) * 0.08 
             + cos(r * 20.0 + theta * 5.0) * 0.035;
  float warpedTheta = theta + fold;

  float rays = 0.0;
  rays += (sin(warpedTheta * 16.0) * 0.5 + 0.5) * 0.45;
  rays += (sin(warpedTheta * 34.0 + 1.2) * 0.5 + 0.5) * 0.28;
  rays += (sin(warpedTheta * 68.0 + 2.5) * 0.5 + 0.5) * 0.17;
  rays += (sin(warpedTheta * 128.0 + 4.1) * 0.5 + 0.5) * 0.10;
  rays = pow(rays, 2.4) * 2.2;

  float crest = sin(r * 8.5 - warpedTheta * 7.0 + fold * 4.5);
  crest = smoothstep(-0.25, 0.75, crest);

  float radialFalloff = smoothstep(0.08, 0.42, r) * smoothstep(1.65, 0.55, r);
  float angularMask = smoothstep(0.05, 0.45, theta) * smoothstep(1.35, 0.85, theta);
  float intensity = rays * crest * radialFalloff * angularMask;
  float ambient = crest * radialFalloff * angularMask * 0.22;

  vec3 c_base   = vec3(0.06, 0.11, 0.05);
  vec3 c_green  = vec3(0.20, 0.33, 0.16);
  vec3 c_bronze = vec3(0.44, 0.28, 0.10);
  vec3 c_neon   = vec3(0.60, 0.30, 1.00);

  vec3 col = mix(c_base, c_green, clamp(ambient * 2.5, 0.0, 1.0));
  col = mix(col, c_bronze, clamp(intensity * 1.4, 0.0, 1.0));

  float specularPeak = pow(clamp(intensity * crest, 0.0, 1.0), 3.5);
  col = mix(col, c_neon, specularPeak * 0.85);

  gl_FragColor = vec4(col, 1.0);
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
                clearValue: { r: 0.06, g: 0.11, b: 0.05, a: 1.0 },
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
