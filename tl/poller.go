package main

import (
	"code.google.com/p/go.net/websocket"
	"fmt"
	"log"
	"strings"
	"time"
)

type PollerRequest struct {
	Command string
	Interval int
	Tags Set
}

type Connection struct {
	ws *websocket.Conn
	interval int
	tags Set
	send chan string
}

type ConnectionPool struct {
	register chan *Connection
	unregister chan *Connection
	connections map[*Connection]bool
}

func (c *Connection) reader() {
	for {
		var (
			msg PollerRequest
			response struct {
				Data string
			}
		)

		if err := websocket.JSON.Receive(c.ws, &msg); err != nil {
			log.Printf("failed to deserialize ws msg: %s", err)
			break
		}

		if len(msg.Tags) > 0 {
			c.tags = msg.Tags
		}

		response.Data = "registered"
		if err := websocket.JSON.Send(c.ws, response); err != nil {
			log.Printf("failed to send register msg: %s", err)
			break
		}
	}

	c.ws.Close()
}

func (c *Connection) writer(metrics MetricsData) {
	for {
		var (
			response struct {
				Data []string
			}
		)

		if len(c.tags) > 0 {
			if filtered := filterByTags(c.tags, metrics); len(filtered) > 0 {
				for _, plugin := range filtered {
					for _, pth := range plugin.Data.ToPath(plugin.Name) {
						response.Data = strings.Fields(pth)
						response.Data = append(response.Data, fmt.Sprintf("%d", time.Now().Unix()*1000))
						if err := websocket.JSON.Send(c.ws, response); err != nil {
							log.Printf("failed to send to ws: %s", err)
							return
						}
					}
				}
			}
		}

		time.Sleep(time.Duration(c.interval) * time.Second)
	}

	c.ws.Close()
}

func (cp *ConnectionPool) run() {
	for {
		select {
		case c := <- cp.register:
			log.Printf("registering: %#v", c)
			cp.connections[c] = true
		case c := <- cp.unregister:
			log.Printf("unregistering: %#v", c)
			delete(cp.connections, c)
			close(c.send)
		}
	}
}
