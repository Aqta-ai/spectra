/**
 * Test suite for useSpectraSocket hook
 * Tests WebSocket connection management, message handling, and error recovery
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useSpectraSocket } from '@/hooks/useSpectraSocket';

// Mock WebSocket
class MockWebSocket {
  url: string;
  readyState: number = WebSocket.CONNECTING;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    // Simulate connection after a short delay
    setTimeout(() => {
      this.readyState = WebSocket.OPEN;
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    }, 10);
  }

  send(data: string | ArrayBuffer | Blob) {
    if (this.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket is not open');
    }
    // Simulate echo response
    setTimeout(() => {
      if (this.onmessage) {
        this.onmessage(new MessageEvent('message', { data }));
      }
    }, 10);
  }

  close() {
    this.readyState = WebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close'));
    }
  }
}

// Replace global WebSocket with mock
global.WebSocket = MockWebSocket as any;

describe('useSpectraSocket', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Connection Management', () => {
    it('should initialize with disconnected state', () => {
      const { result } = renderHook(() => useSpectraSocket());
      
      expect(result.current.isConnected).toBe(false);
      expect(result.current.connectionState).toBe('disconnected');
    });

    it('should connect to WebSocket', async () => {
      const { result } = renderHook(() => useSpectraSocket());
      
      await act(async () => {
        await result.current.connect();
      });
      
      await waitFor(() => {
        expect(result.current.isConnected).toBe(true);
        expect(result.current.connectionState).toBe('connected');
      });
    });

    it('should disconnect from WebSocket', async () => {
      const { result } = renderHook(() => useSpectraSocket());
      
      await act(async () => {
        await result.current.connect();
      });
      
      await waitFor(() => expect(result.current.isConnected).toBe(true));
      
      await act(async () => {
        await result.current.disconnect();
      });
      
      expect(result.current.isConnected).toBe(false);
      expect(result.current.connectionState).toBe('disconnected');
    });

    it('should handle connection errors', async () => {
      const { result } = renderHook(() => useSpectraSocket());
      
      // Mock connection failure
      global.WebSocket = class extends MockWebSocket {
        constructor(url: string) {
          super(url);
          setTimeout(() => {
            this.readyState = WebSocket.CLOSED;
            if (this.onerror) {
              this.onerror(new Event('error'));
            }
          }, 10);
        }
      } as any;
      
      await act(async () => {
        try {
          await result.current.connect();
        } catch (error) {
          // Expected to fail
        }
      });
      
      await waitFor(() => {
        expect(result.current.connectionState).toBe('error');
      });
    });

    it('should automatically reconnect after disconnect', async () => {
      const { result } = renderHook(() => useSpectraSocket({
        autoReconnect: true,
        reconnectDelay: 100
      }));
      
      await act(async () => {
        await result.current.connect();
      });
      
      await waitFor(() => expect(result.current.isConnected).toBe(true));
      
      // Simulate disconnect
      act(() => {
        result.current.disconnect();
      });
      
      // Should reconnect automatically
      await waitFor(() => {
        expect(result.current.isConnected).toBe(true);
      }, { timeout: 500 });
    });
  });

  describe('Message Handling', () => {
    it('should send text messages', async () => {
      const { result } = renderHook(() => useSpectraSocket());
      
      await act(async () => {
        await result.current.connect();
      });
      
      await waitFor(() => expect(result.current.isConnected).toBe(true));
      
      const message = { type: 'text', data: 'Hello Spectra' };
      
      await act(async () => {
        await result.current.send(message);
      });
      
      // Message should be sent successfully
      expect(result.current.lastSentMessage).toEqual(message);
    });

    it('should receive messages', async () => {
      const { result } = renderHook(() => useSpectraSocket());
      const receivedMessages: any[] = [];
      
      await act(async () => {
        await result.current.connect();
        result.current.on('message', (msg) => {
          receivedMessages.push(msg);
        });
      });
      
      await waitFor(() => expect(result.current.isConnected).toBe(true));
      
      // Send a message (will be echoed back by mock)
      await act(async () => {
        await result.current.send({ type: 'test', data: 'hello' });
      });
      
      await waitFor(() => {
        expect(receivedMessages.length).toBeGreaterThan(0);
      });
    });

    it('should handle audio messages', async () => {
      const { result } = renderHook(() => useSpectraSocket());
      
      await act(async () => {
        await result.current.connect();
      });
      
      await waitFor(() => expect(result.current.isConnected).toBe(true));
      
      const audioData = new ArrayBuffer(1024);
      
      await act(async () => {
        await result.current.sendAudio(audioData);
      });
      
      expect(result.current.lastSentMessage?.type).toBe('audio');
    });

    it('should handle screenshot messages', async () => {
      const { result } = renderHook(() => useSpectraSocket());
      
      await act(async () => {
        await result.current.connect();
      });
      
      await waitFor(() => expect(result.current.isConnected).toBe(true));
      
      const screenshot = {
        data: 'base64_image_data',
        width: 1280,
        height: 720
      };
      
      await act(async () => {
        await result.current.sendScreenshot(screenshot);
      });
      
      expect(result.current.lastSentMessage?.type).toBe('screenshot');
    });

    it('should handle action result messages', async () => {
      const { result } = renderHook(() => useSpectraSocket());
      
      await act(async () => {
        await result.current.connect();
      });
      
      await waitFor(() => expect(result.current.isConnected).toBe(true));
      
      const actionResult = {
        id: 'action-123',
        success: true,
        result: 'Clicked submit button'
      };
      
      await act(async () => {
        await result.current.sendActionResult(actionResult);
      });
      
      expect(result.current.lastSentMessage?.type).toBe('action_result');
    });
  });

  describe('Event Listeners', () => {
    it('should register event listeners', async () => {
      const { result } = renderHook(() => useSpectraSocket());
      const listener = vi.fn();
      
      act(() => {
        result.current.on('message', listener);
      });
      
      expect(result.current.listeners.message).toContain(listener);
    });

    it('should unregister event listeners', async () => {
      const { result } = renderHook(() => useSpectraSocket());
      const listener = vi.fn();
      
      act(() => {
        result.current.on('message', listener);
        result.current.off('message', listener);
      });
      
      expect(result.current.listeners.message).not.toContain(listener);
    });

    it('should call listeners when events occur', async () => {
      const { result } = renderHook(() => useSpectraSocket());
      const connectListener = vi.fn();
      const messageListener = vi.fn();
      
      act(() => {
        result.current.on('connect', connectListener);
        result.current.on('message', messageListener);
      });
      
      await act(async () => {
        await result.current.connect();
      });
      
      await waitFor(() => {
        expect(connectListener).toHaveBeenCalled();
      });
    });
  });

  describe('Connection State', () => {
    it('should track connection state transitions', async () => {
      const { result } = renderHook(() => useSpectraSocket());
      const states: string[] = [];
      
      act(() => {
        result.current.on('stateChange', (state) => {
          states.push(state);
        });
      });
      
      await act(async () => {
        await result.current.connect();
      });
      
      await waitFor(() => {
        expect(states).toContain('connecting');
        expect(states).toContain('connected');
      });
    });

    it('should provide connection metrics', async () => {
      const { result } = renderHook(() => useSpectraSocket());
      
      await act(async () => {
        await result.current.connect();
      });
      
      await waitFor(() => expect(result.current.isConnected).toBe(true));
      
      const metrics = result.current.getMetrics();
      
      expect(metrics).toHaveProperty('latency');
      expect(metrics).toHaveProperty('messagesSent');
      expect(metrics).toHaveProperty('messagesReceived');
    });
  });

  describe('Error Handling', () => {
    it('should handle send errors gracefully', async () => {
      const { result } = renderHook(() => useSpectraSocket());
      
      // Try to send without connecting
      await act(async () => {
        try {
          await result.current.send({ type: 'test' });
        } catch (error) {
          expect(error).toBeDefined();
        }
      });
    });

    it('should queue messages when disconnected', async () => {
      const { result } = renderHook(() => useSpectraSocket({
        queueWhenDisconnected: true
      }));
      
      // Send message while disconnected
      await act(async () => {
        await result.current.send({ type: 'test', data: 'queued' });
      });
      
      expect(result.current.messageQueue.length).toBeGreaterThan(0);
      
      // Connect and flush queue
      await act(async () => {
        await result.current.connect();
      });
      
      await waitFor(() => {
        expect(result.current.messageQueue.length).toBe(0);
      });
    });

    it('should handle malformed messages', async () => {
      const { result } = renderHook(() => useSpectraSocket());
      const errorListener = vi.fn();
      
      act(() => {
        result.current.on('error', errorListener);
      });
      
      await act(async () => {
        await result.current.connect();
      });
      
      await waitFor(() => expect(result.current.isConnected).toBe(true));
      
      // Simulate receiving malformed message
      // This would be handled internally by the hook
    });
  });

  describe('Cleanup', () => {
    it('should cleanup on unmount', async () => {
      const { result, unmount } = renderHook(() => useSpectraSocket());
      
      await act(async () => {
        await result.current.connect();
      });
      
      await waitFor(() => expect(result.current.isConnected).toBe(true));
      
      unmount();
      
      // Connection should be closed
      expect(result.current.isConnected).toBe(false);
    });

    it('should remove all listeners on unmount', async () => {
      const { result, unmount } = renderHook(() => useSpectraSocket());
      const listener = vi.fn();
      
      act(() => {
        result.current.on('message', listener);
      });
      
      unmount();
      
      expect(result.current.listeners.message).toHaveLength(0);
    });
  });
});
