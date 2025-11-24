# phoque - Easy TUI Firewall

## Project Description:
TUI firewall much like UFW, easy to use and to setup

## Diagram:
```cpp
classDiagram
    class IDatabaseService {
        <<Interface>>
        +save(rules: List~Rule~)
        +load() List~Rule~
    }

    class JsonDatabase {
        <<Singleton>>
        -static instance: JsonDatabase
        -file_path: str
        -JsonDatabase()
        +get_instance() JsonDatabase$
        +save(rules: List~Rule~)
        +load() List~Rule~
    }

    class Rule {
        <<Abstract>>
        +UUID id
        +Direction direction
        +Protocol protocol
        +int port
        +get_command() str*
    }

    class AllowRule {
        +get_command() str
    }

    class DenyRule {
        +get_command() str
    }

    class RejectRule {
        +get_command() str
    }

    class Direction {
        <<enumeration>>
        IN
        OUT
        FORWARD
    }
    class Protocol {
        <<enumeration>>
        TCP
        UDP
        ICMP
    }

    class FirewallManager {
        -List~Rule~ rules
        -IDatabaseService db
        +add_rule(Rule rule)
        +remove_rule(uuid)
        +apply_configuration()
    }

    %% --- Relations ---
    JsonDatabase --|> IDatabaseService : implements
    IDatabaseService ..> Rule : manages

    AllowRule --|> Rule : inherits
    DenyRule --|> Rule : inherits
    RejectRule --|> Rule : inherits

    Rule ..> Direction
    Rule ..> Protocol

    FirewallManager --> IDatabaseService : uses
    FirewallManager o-- Rule : aggregates
```